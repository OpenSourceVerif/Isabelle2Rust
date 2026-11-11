(* Execute Isabelle's registered code_printing functions in an isolated Rust
   target. The JSON contains rendered applications, never serialized closures.
   This intentionally does not run the full Rust algorithm serializer. *)
structure I2R_Adapter_Export =
struct
open Basic_Code_Thingol Basic_Code_Symbol;
open I2R_Agent_Export;

val requested = Unsynchronized.ref ([] : string list);
val source_names = Unsynchronized.ref ([] : string list);
val source_types = Unsynchronized.ref ([] : string list);

fun pretty p = Pretty.unformatted_string_of p;
fun split_fun ("fun" `%% [a,b]) = let val (args,r) = split_fun b in (a::args,r) end
  | split_fun ty = ([],ty);

val literals = Code_Printer.Literals {
  literal_string = quote,
  literal_numeral = fn k => if k < 0 then "-" ^ Int.toString (~k) else Int.toString k,
  literal_list = Code_Printer.enum "," "[" "]", infix_cons = (6,"::")};

val serializer : Code_Target.serializer = fn _ => fn ctxt =>
  fn {module_name,tyco_syntax,const_syntax,includes,identifiers,reserved_syms,...} =>
  fn program => fn exports =>
  let
    val entries = if null (!requested) then map_filter (fn Constant c => SOME c | _ => NONE) exports else !requested;
    val raw = Code_Thingol.consts_program ctxt entries;
    val symbols = distinct (op =) (Code_Symbol.Graph.keys raw @
      map Constant (!source_names) @ map Type_Constructor (!source_types));
    fun print_type fix (ITyVar a) = Pretty.str a
      | print_type fix (name `%% args) =
          (case tyco_syntax name of
             SOME (_,pr) => pr print_type fix args
           | NONE => Pretty.str ("SOURCE_TYPE[" ^ name ^
               (if null args then "" else ":" ^ commas (map (pretty o print_type Code_Printer.NOBR) args)) ^ "]"));
    fun print_term vars fix (IVar (SOME name)) = Pretty.str (Code_Printer.lookup_var vars name)
      | print_term _ _ (IVar NONE) = Pretty.str "_"
      | print_term vars fix t =
          (case Code_Thingol.unfold_const_app t of
             SOME app => Code_Printer.gen_print_app
               (fn _ => fn v => fn ({sym,...},args) =>
                 [Pretty.str ("SOURCE_CONSTANT[" ^ I2R_Agent_Export.sym sym ^ "](" ^
                   commas (map (pretty o print_term v Code_Printer.NOBR) args) ^ ")")])
               (fn _ => print_term) const_syntax NONE vars fix app
           | NONE => Pretty.str "SOURCE_TERM[see preserved Thingol]");
    val applications = Unsynchronized.ref ([] : (Code_Symbol.T * iterm) list);
    fun collect owner t =
      let
        val _ = (case Code_Thingol.unfold_const_app t of
          SOME ({sym=Constant name,...},_) =>
            if is_some (const_syntax name) then applications := (owner,t) :: !applications else ()
        | _ => ());
        val _ = (case t of
            a `$ b => (ignore (collect owner a); ignore (collect owner b))
          | _ `|=> (body,_) => ignore (collect owner body)
          | ICase {term,clauses,primitive,...} =>
              (ignore (collect owner term); ignore (collect owner primitive);
               List.app (fn (p,b) => (ignore (collect owner p); ignore (collect owner b))) clauses)
          | _ => ());
      in t end;
    val _ = List.app (fn (symbol,statement) =>
      ignore (Code_Thingol.map_terms_stmt (collect symbol) statement)) (Code_Symbol.Graph.dest raw |> map fst);
    fun captured action =
      (case Exn.capture action () of
        Exn.Res body => obj [("status",quote "rendered"),("rust",quote body)]
      | Exn.Exn e => obj [("status",quote "requires_concrete_application"),("error",quote (Runtime.exn_message e))]);
    fun type_binding (Type_Constructor name) =
          (case tyco_syntax name of NONE => NONE | SOME (arity,pr) =>
             let val args = map (fn i => ITyVar ("T" ^ Int.toString i)) (0 upto (arity - 1))
             in SOME (obj [("source",quote (sym (Type_Constructor name))),
               ("arity",Int.toString arity),("application",captured (fn () => pretty (pr print_type Code_Printer.NOBR args)))]) end)
      | type_binding _ = NONE;
    fun source_signature name =
      (case (if Code_Symbol.Graph.defined raw (Constant name)
             then SOME (Code_Symbol.Graph.get_node raw (Constant name)) else NONE) of
         SOME (Code_Thingol.Fun (((_,ty),_),_)) => split_fun ty
       | _ => (case get_first (fn (_,t) => case Code_Thingol.unfold_const_app t of
             SOME ({sym=Constant c,dom,range,...},_) => if c=name then SOME (dom,range) else NONE
           | _ => NONE) (!applications) of SOME signature_parts => signature_parts
             | NONE => ([],ITyVar "result")));
    fun operation_binding (Constant name) =
          (case const_syntax name of NONE => NONE | SOME (arity,printer) =>
            let
              val (dom,range) = source_signature name;
              val names = map (fn i => "argument" ^ Int.toString i) (0 upto (arity - 1));
              val vars = Code_Printer.make_vars names;
              val args = map_index (fn (i,n) => (IVar (SOME n),
                if i < length dom then nth dom i else ITyVar ("A" ^ Int.toString i))) names;
              fun render () = (case printer of
                  Code_Printer.Plain_printer s => s ^
                    (if null names then "" else "(" ^ commas names ^ ")")
                | Code_Printer.Complex_printer pr =>
                    pretty (pr print_term NONE vars Code_Printer.NOBR args));
            in SOME (obj [("source",quote (sym (Constant name))),
               ("active_in_adapter_graph",if Code_Symbol.Graph.defined raw (Constant name) then "true" else "false"),
               ("arity",Int.toString arity),("parameters",arr quote names),
               ("source_domain",arr typ dom),("source_range",typ range),
               ("application",captured render)]) end)
      | operation_binding _ = NONE;
    val types = map_filter type_binding symbols;
    val operations = map_filter operation_binding symbols;
    fun application_record (owner,t) = obj [
      ("owner",quote (sym owner)),("thingol",term t),
      ("application",captured (fn () => pretty
        (print_term (Code_Printer.make_vars (Code_Thingol.add_varnames t [])) Code_Printer.NOBR t)))];
    val concrete = map application_record (rev (!applications));
    val support = map (fn (name,code) => obj [("module",quote name),("code",quote (Pretty.pure_string_of code))]) includes;
    val data = obj [("schema_version","1"),("target",quote "Rust"),
      ("types",arr I types),("operations",arr I operations),("concrete_applications",arr I concrete),("support_modules",arr I support),
      ("original_entries",arr (quote o sym o Constant) entries),
      ("note",quote "Rendered placeholders and actual source applications using the active Isabelle printers. Unresolved nested terms remain marked SOURCE_TERM/SOURCE_CONSTANT; this is not proof or automatic enforcement of LLM output.")];
    val exported = [(["adapter-bindings.json"],Pretty.str data),
      (["source-model.json"],Pretty.str (I2R_Source_Model.export ctxt entries)),
      (["program.json"],Pretty.str (program_json ctxt module_name program exports)),
      (["source-index.json"],Pretty.str (source_index ctxt)),
      (["adapter-before-target.json"],Pretty.str (program_json ctxt module_name raw (map Constant entries))),
      (["adapter-after-target.json"],Pretty.str (program_json ctxt module_name program exports))];
  in (Code_Target.Hierarchy exported,SOME o sym) end;

end;
