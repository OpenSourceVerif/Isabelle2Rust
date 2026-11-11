(* Isabelle facts for the agent-owned program model. No Thingol types or graph
   are consumed here. Proof objects remain in Isabelle; theorem propositions
   and provenance are exported, not a purported Rust correctness certificate. *)
structure I2R_Source_Model =
struct
fun quote s = "\"" ^ String.translate (fn c => case c of
    #"\"" => "\\\"" | #"\\" => "\\\\" | #"\n" => "\\n" | #"\r" => "\\r" | #"\t" => "\\t"
  | _ => if Char.ord c < 32 then " " else String.str c) s ^ "\"";
fun arr f xs = "[" ^ commas (map f xs) ^ "]";
fun obj xs = "{" ^ commas (map (fn (k,v) => quote k ^ ":" ^ v) xs) ^ "}";
fun opt f NONE = "null" | opt f (SOME x) = f x;
fun bool b = if b then "true" else "false";
fun variable (n,s) = obj [("name",quote n),("sort",arr quote s)];
fun typ (Type (n,ts)) = obj [("kind",quote "type"),("name",quote n),("args",arr typ ts)]
  | typ (TFree (n,s)) = obj [("kind",quote "free"),("name",quote n),("sort",arr quote s)]
  | typ (TVar ((n,i),s)) = obj [("kind",quote "schematic"),("name",quote n),("index",Int.toString i),("sort",arr quote s)];
fun term (Const (n,t)) = obj [("kind",quote "const"),("name",quote n),("type",typ t)]
  | term (Free (n,t)) = obj [("kind",quote "free"),("name",quote n),("type",typ t)]
  | term (Var ((n,i),t)) = obj [("kind",quote "schematic"),("name",quote n),("index",Int.toString i),("type",typ t)]
  | term (Bound i) = obj [("kind",quote "bound"),("index",Int.toString i)]
  | term (Abs (n,t,b)) = obj [("kind",quote "lambda"),("binder",quote n),("type",typ t),("body",term b)]
  | term (f $ x) = obj [("kind",quote "apply"),("function",term f),("argument",term x)];
fun plain s = XML.content_of (YXML.parse_body s);
fun pretty ctxt t = plain (Syntax.string_of_term ctxt t);
fun evidence ctxt t = obj [("text",quote (pretty ctxt t)),("term",term t)];
fun theorem ctxt th = obj [("name",quote (#1 (Thm.get_name_hint th))),
  ("proposition",evidence ctxt (Thm.prop_of th))];

fun export ctxt entries =
  let
    val thy = Proof_Context.theory_of ctxt;
    val {eqngr,...} = Code_Preproc.obtain true {ctxt=ctxt,consts=entries,terms=[]};
    val names = sort_strings (Code_Preproc.all eqngr);
    val used_types = Unsynchronized.ref ([] : typ list);
    fun track t = (used_types := t :: !used_types; typ t);
    fun track_term t = (used_types := Term.fold_types (insert (op =)) t (!used_types); term t);
    fun spec ({pos,name,rough_classification,terms,rules}: Spec_Rules.spec_rule) = obj [
      ("name",quote name),("file",opt quote (Position.file_of pos)),("line",opt Int.toString (Position.line_of pos)),
      ("equational",bool (Spec_Rules.is_equational rough_classification)),
      ("rules",arr (theorem ctxt) rules)];
    fun entity c =
      let
        val ((vs,T),eqns) = Code.equations_of_cert thy (Code_Preproc.cert eqngr c);
        val sourceT = Sign.the_const_type thy c;
        val ct = Const (c,sourceT);
        val inputs = (case Function_Common.import_function_data ct ctxt of
          SOME info => #input_eqns info | NONE => []);
        fun arg (abs,t) = obj [("abstraction",opt quote abs),("term",track_term t),("text",quote (pretty ctxt t))];
        fun equation ((args,rhs),(proof,proper)) = obj [("arguments",arr arg args),("rhs",arg rhs),
          ("theorem",opt (theorem ctxt) proof),("proper",bool proper)];
        val deps = distinct (op =) (maps (fn ((args,rhs),_) =>
          maps (fn (_,t) => Term.add_const_names t []) (rhs::args)) (these eqns));
        val occurrences = distinct (op =) (maps (fn ((args,rhs),_) =>
          maps (fn (_,t) => Term.add_consts t []) (rhs::args)) (these eqns));
        fun resolution (name,T) = obj [("constant",quote name),("type",typ T),
          ("implementation",quote (Axclass.unoverload_const thy (name,T)))];
      in obj [("id",quote ("constant:" ^ c)),("name",quote c),("kind",quote "constant"),
        ("source_type",track sourceT),("execution_type",track T),("type_variables",arr variable vs),
        ("execution_sorts",arr (arr quote) (Code_Preproc.sortargs eqngr c)),
        ("instance_identity",opt (fn (name,tyco) => obj [("parameter",quote name),("type_constructor",quote tyco)]) (Axclass.inst_of_param thy c)),
        ("instance_resolutions",arr resolution occurrences),
        ("specifications",arr spec (Spec_Rules.retrieve ctxt ct)),
        ("function_input_equations",arr (evidence ctxt) inputs),
        ("execution_equations",opt (arr equation) eqns),
        ("dependencies",arr (quote o prefix "constant:") (sort_strings deps))] end;
    val constants = map entity names;
    fun type_names (Type (n,ts)) = n :: maps type_names ts | type_names _ = [];
    fun type_closure [] seen rows = rev rows
      | type_closure (n::todo) seen rows = if member (op =) seen n then type_closure todo seen rows else
        let
          val ((vs,cs),abstract) = Code.get_type thy n;
          val fields = maps (snd o snd) cs;
          val _ = used_types := fields @ !used_types;
          fun constructor (c,(vars,ts)) = obj [("id",quote ("constant:" ^ c)),
            ("variables",arr variable vars),("fields",arr typ ts)];
          val row = obj [("id",quote ("type:" ^ n)),("name",quote n),("kind",quote "type"),
            ("variables",arr variable vs),("abstract",bool abstract),("constructors",arr constructor cs)];
        in type_closure (todo @ maps type_names fields) (n::seen) (row::rows) end;
    val types = type_closure (sort_strings (distinct (op =) (maps type_names (!used_types)))) [] [];
    fun type_sorts (Type (_,ts)) = maps type_sorts ts
      | type_sorts (TFree (_,s)) = s | type_sorts (TVar (_,s)) = s;
    val classes = distinct (op =) (maps type_sorts (!used_types));
    fun class_closure [] seen rows = rev rows
      | class_closure (c::todo) seen rows = if member (op =) seen c then class_closure todo seen rows else
        let
          val supers = Sorts.super_classes (Sign.classes_of thy) c;
          val params = (case try (Axclass.get_info thy) c of SOME info => #params info | NONE => []);
          val row = obj [("id",quote ("class:" ^ c)),("name",quote c),("kind",quote "class"),
            ("supers",arr (quote o prefix "class:") supers),
            ("parameters",arr (fn (n,T) => obj [("id",quote ("constant:" ^ n)),("type",typ T)]) params)];
        in class_closure (todo @ supers) (c::seen) (row::rows) end;
  in obj [("schema_version","1"),("origin",quote "Isabelle context: Spec_Rules, Function_Common, Code_Preproc, Code.get_type, Axclass"),
    ("entries",arr (quote o prefix "constant:") entries),("entities",arr I (constants @ types @ class_closure classes [] [])),
    ("limits",quote "Typed elaborated terms, not original concrete syntax. Execution equations are preprocessed. Proof terms are not exported. Dependencies are constant occurrences, not inferred alias/liveness facts. Native bindings are separate evidence.")]
  end;
end;
