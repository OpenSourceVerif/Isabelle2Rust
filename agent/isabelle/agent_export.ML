(* Structured serialization of the actual code-generator program.
   No Rust text or source-reference executable is used as the agent input. *)
structure I2R_Agent_Export =
struct
open Basic_Code_Thingol;
open Basic_Code_Symbol;

fun quote s = "\"" ^ String.translate (fn c =>
    case c of #"\"" => "\\\"" | #"\\" => "\\\\" | #"\n" => "\\n"
      | #"\r" => "\\r" | #"\t" => "\\t"
      | _ => if Char.ord c < 32 then " " else String.str c) s ^ "\"";
fun arr f xs = "[" ^ commas (map f xs) ^ "]";
fun obj xs = "{" ^ commas (map (fn (k,v) => quote k ^ ":" ^ v) xs) ^ "}";
fun pair f g (a,b) = arr I [f a,g b];
fun opt f NONE = "null" | opt f (SOME x) = f x;
fun boolean b = if b then "true" else "false";
fun sym (Constant s) = "constant:" ^ s
  | sym (Type_Constructor s) = "type:" ^ s
  | sym (Type_Class s) = "class:" ^ s
  | sym (Class_Relation (a,b)) = "classrel:" ^ a ^ ":" ^ b
  | sym (Class_Instance (a,b)) = "instance:" ^ a ^ ":" ^ b
  | sym (Module s) = "module:" ^ s;
fun typ (ITyVar x) = obj [("var",quote x)]
  | typ (name `%% args) = obj [("constructor",quote name),("args",arr typ args)];
fun dict (Dict (rels,d)) = obj [("relations",arr (pair quote quote) rels),("dictionary",plain d)]
and plain (Dict_Const ((t,c),args)) = obj [("type",quote t),("class",quote c),("args",arr (pair typ (arr dict)) args)]
  | plain (Dict_Var {var,index,length,class,unique}) = obj [("var",quote var),("index",Int.toString index),
      ("length",Int.toString length),("class",quote class),("unique",boolean unique)];
fun const {sym=s,typargs,dicts,dom,range,annotation} = obj [("symbol",quote (sym s)),
  ("type_args",arr typ typargs),("dicts",arr (arr dict) dicts),("domain",arr typ dom),
  ("range",typ range),("annotation",opt typ annotation)];
fun term (IConst c) = obj [("const",const c)]
  | term (IVar v) = obj [("var",opt quote v)]
  | term (f `$ x) = obj [("application",arr term [f,x])]
  | term ((v,t) `|=> (b,bt)) = obj [("lambda",obj [("name",opt quote v),("type",typ t),("body",term b),("body_type",typ bt)])]
  | term (ICase {term=t,typ=ty,clauses,primitive}) = obj [("case",obj [("term",term t),("type",typ ty),
      ("clauses",arr (pair term term) clauses),("primitive",term primitive)])];
fun scheme (vs,t) = obj [("variables",arr (pair quote (arr quote)) vs),("type",typ t)];
fun thm ctxt t = obj [("name",quote (#1 (Thm.get_name_hint t))),("proposition",quote (XML.content_of (YXML.parse_body (Syntax.string_of_term ctxt (Thm.prop_of t)))))];
fun stmt ctxt Code_Thingol.NoStmt = obj [("kind",quote "unimplemented")]
  | stmt ctxt (Code_Thingol.Fun ((ty,eqs),cong)) = obj [("kind",quote "function"),("signature",scheme ty),
      ("equations",arr (fn ((args,body),(proof,flag)) => obj [("args",arr term args),("body",term body),
        ("source_theorem",opt (thm ctxt) proof),("flag",boolean flag)]) eqs),("congruence",opt (thm ctxt) cong)]
  | stmt _ (Code_Thingol.Datatype (vs,cs)) = obj [("kind",quote "datatype"),("variables",arr quote vs),
      ("constructors",arr (pair (pair quote (arr quote)) (arr typ)) cs)]
  | stmt _ (Code_Thingol.Datatypecons t) = obj [("kind",quote "constructor"),("datatype",quote t)]
  | stmt _ (Code_Thingol.Class (v,(sup,params))) = obj [("kind",quote "class"),("variable",quote v),
      ("supers",arr (pair quote quote) sup),("parameters",arr (pair quote typ) params)]
  | stmt _ (Code_Thingol.Classrel (a,b)) = obj [("kind",quote "class_relation"),("relation",pair quote quote (a,b))]
  | stmt _ (Code_Thingol.Classparam c) = obj [("kind",quote "class_parameter"),("class",quote c)]
  | stmt ctxt (Code_Thingol.Classinst {class,tyco,vs,superinsts,inst_params,superinst_params}) =
      let fun param ((name,(c,n)),(proof,flag)) = obj [("name",quote name),("const",const c),("arity",Int.toString n),
             ("source_theorem",thm ctxt proof),("flag",boolean flag)]
      in obj [("kind",quote "instance"),("class",quote class),("type",quote tyco),
          ("variables",arr (pair quote (arr quote)) vs),("supers",arr (pair quote (arr (pair typ (arr dict)))) superinsts),
          ("parameters",arr param inst_params),("super_parameters",arr param superinst_params)] end;

fun program_json ctxt module_name program exports =
  let
    val nodes = Code_Symbol.Graph.dest program;
  in obj [("schema_version","1"),("module_name",quote module_name),
      ("entries",arr (quote o sym) exports),
      ("nodes",arr (fn ((s,st),deps) => obj [("id",quote (sym s)),("statement",stmt ctxt st),
        ("dependencies",arr (quote o sym) deps)]) nodes),
      ("sccs",arr (arr (quote o sym)) (Code_Symbol.Graph.strong_conn program))] end;

fun source_index ctxt =
  let
    fun item thy =
      let
        val name = Context.theory_long_name thy;
        val file = Resources.master_directory thy + Path.basic (Context.theory_base_name thy ^ ".thy");
      in obj [("theory",quote name),("base_name",quote (Context.theory_base_name thy)),
        ("path",quote (File.platform_path file)),
        ("imports",arr (quote o fst) (Resources.imports_of thy))] end;
  in obj [("theories",arr item (Theory.nodes_of (Proof_Context.theory_of ctxt)))] end;

val serializer : Code_Target.serializer = fn _ => fn ctxt => fn {module_name,...} => fn program => fn exports =>
  let
    val consts = map_filter (fn Constant c => SOME c | _ => NONE) exports;
    val raw = Code_Thingol.consts_program ctxt consts;
  in (Code_Target.Hierarchy
    ((["program.json"],Pretty.str (program_json ctxt module_name program exports)) ::
     [(["before-target.json"],Pretty.str (program_json ctxt module_name raw exports)),
      (["source-model.json"],Pretty.str (I2R_Source_Model.export ctxt consts)),
      (["source-index.json"],Pretty.str (source_index ctxt))]), SOME o sym) end;

end;
