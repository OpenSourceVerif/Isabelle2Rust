signature CODE_DEBUG_INFO = 
sig
  type itype
  type iterm
  type const
  type dict
  type plain_dict

  type stmt

  type sym

  val wrap_args : string list -> string
  val wrap_list : string list -> string
  val wrap_struct : string list -> string

  val print_debug_info_itype : itype -> string
  val print_debug_info_dict : dict -> string
  val print_plain_dict : plain_dict -> string

  val print_debug_info_sym : sym -> string

  val print_debug_info_const :
    { sym : sym,
      typargs : itype list,
      dicts : dict list list,
      dom : itype list,
      range : itype,
      annotation : itype option } -> string

  val dest_vname : string option -> string

  val print_debug_info_iterm : iterm -> string

  val dest_typscheme :
    (string * string list) list * itype -> string

  val print_debug_info_thingol_stmt :
    stmt -> string

  val print_debug_info_node :
    (sym * stmt) * sym list -> string

end

structure Code_Debug_Info : CODE_DEBUG_INFO =
struct

open Basic_Code_Symbol;     
open Basic_Code_Thingol;
open Code_Printer;  

type itype = Code_Thingol.itype
type iterm = Code_Thingol.iterm
type const = Code_Thingol.const
type dict = Code_Thingol.dict
type plain_dict = Code_Thingol.plain_dict

type stmt = Code_Thingol.stmt

type sym = Code_Symbol.T

(** print debug info **)

fun wrap_args sl = "(" ^ String.concatWith ", " sl ^ ")"
fun wrap_list sl = "[" ^ String.concatWith ", " sl ^ "]"
fun wrap_struct sl = "{" ^ String.concatWith ", " sl ^ "}"
fun print_debug_info_itype (ITyVar itypvn) = itypvn
  | print_debug_info_itype (vn `%% itypes) = 
    vn ^"`%%"^ wrap_list (map print_debug_info_itype itypes) 
fun print_debug_info_dict (Dict (classrels, plain_dict)) = 
  let 
    fun print_classrels classrels  = 
      wrap_list (map (fn (s1, s2) => wrap_args [s1, s2]) classrels) (*type class = string*)
  in
    "Dict="^wrap_args [print_classrels classrels , print_plain_dict plain_dict]
  end
and print_plain_dict (Dict_Const ((s, c), args)) = 
    "Dict_Const="^wrap_args [(wrap_args [s, c]),
      wrap_list (map (fn (ityp, dicts) =>
        wrap_args [(print_debug_info_itype ityp), wrap_list (map print_debug_info_dict dicts)]) args)]  
  | print_plain_dict (Dict_Var {var, index, length, class, unique}) = 
    "Dict_Var="^wrap_struct ["var: "^var, "index: "^Int.toString index, "length: "^Int.toString length, 
      "class: "^class, "unique: "^Bool.toString unique]
fun print_debug_info_sym sym = case sym of
    Constant a => "Constant="^a 
    | Type_Constructor b => "Type_Constructor="^b
    | Type_Class c =>"Type_Class="^ c 
    | Class_Relation (d1, d2) => "Class_Relation="^wrap_args [d1, d2]
    | Class_Instance (e1, e2) => "Class_Instance="^wrap_args [e1, e2]
    | Module f => "Module"^f 
fun print_debug_info_const {sym, typargs, dicts, dom, range, annotation} = 
  let 
    val sym_base = print_debug_info_sym sym
    val annot = case annotation of 
      NONE => "NONE"
      | SOME a => print_debug_info_itype a
  in
    wrap_struct ["sym: "^sym_base, "typargs: "^wrap_list (map print_debug_info_itype typargs),
      "dicts: "^wrap_list ((map (wrap_list o (map print_debug_info_dict)) dicts)),
      "dom: "^wrap_list (map print_debug_info_itype dom),
      "range: "^print_debug_info_itype range, "annotation: "^annot]
  end
fun dest_vname v = case v of
  NONE => "Anonymous"
  | SOME vname => vname
fun print_debug_info_iterm (IConst const) = 
    print_debug_info_const const
  | print_debug_info_iterm (IVar vname) = 
    dest_vname vname
  | print_debug_info_iterm (t1 `$ t2) =
    "(" ^ print_debug_info_iterm t1 ^ "`$" ^ print_debug_info_iterm t2 ^ ")"
  | print_debug_info_iterm ((v, ityp1) `|=> (t, ityp2)) =
    wrap_args [wrap_args [dest_vname v, print_debug_info_itype ityp1], 
      wrap_args [print_debug_info_iterm t, print_debug_info_itype ityp2]]
  | print_debug_info_iterm (ICase {term, typ, clauses, primitive}) =
    wrap_struct ["term: "^print_debug_info_iterm term, "typ: "^print_debug_info_itype typ,
    "clauses: "^wrap_list (map (fn (t1, t2) 
      => wrap_args [print_debug_info_iterm t1, print_debug_info_iterm t2]) clauses),
    "primitive: "^print_debug_info_iterm primitive]
fun dest_typscheme (s, t) = 
  wrap_args [wrap_list (map (fn (t1, t2) => wrap_args [t1, wrap_list t2]) s), print_debug_info_itype t]
fun print_debug_info_thingol_stmt Code_Thingol.NoStmt = 
    "NoStmt"
  | print_debug_info_thingol_stmt (Code_Thingol.Fun ((scheme, args), _)) = 
    "Fun="^wrap_args ["typscheme="^dest_typscheme scheme, "patterns="^wrap_list (map (fn ((ts, t), _) =>
      wrap_args [wrap_list (map print_debug_info_iterm ts)]^"=>"^print_debug_info_iterm t) args)]
  | print_debug_info_thingol_stmt (Code_Thingol.Datatype (vns, cos)) = 
    "Datatype="^wrap_args [wrap_list vns, wrap_list (map (fn ((v, args), itypes) => 
      wrap_args [wrap_args [v, wrap_list args], wrap_list (map print_debug_info_itype itypes)]) cos)]
  | print_debug_info_thingol_stmt (Code_Thingol.Datatypecons v) = 
    "Datatypecons="^v   
  | print_debug_info_thingol_stmt (Code_Thingol.Class (c, (rels, params))) = 
    "Class="^wrap_args [c, "rels="^wrap_list (map (fn (c1, c2) => wrap_args [c1, c2]) rels),
      "params="^wrap_list (map (fn (s,t) => wrap_args [s, print_debug_info_itype t]) params)]
  | print_debug_info_thingol_stmt (Code_Thingol.Classrel (c1, c2)) = 
    "Classrel="^wrap_args[c1, c2]
  | print_debug_info_thingol_stmt (Code_Thingol.Classparam p) = 
    "Classparam="^p         
  | print_debug_info_thingol_stmt (Code_Thingol.Classinst {class, tyco, vs, ...}) = 
    "Classinst="^wrap_struct ["class: "^class, "tyco: "^tyco, 
      "vs: "^wrap_list (map (fn (t1, t2) => wrap_args [t1, wrap_list t2]) vs), "..."]
fun print_debug_info_node ((sym, stmt), syms) =
  wrap_struct [ "key: "^print_debug_info_sym sym, "stmt: "^print_debug_info_thingol_stmt stmt,
   "children: "^wrap_list (map print_debug_info_sym syms)]


end