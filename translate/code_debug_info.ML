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

(* Debug strings describe the recognized Thingol view, which may itself contain
   shared branches. Emit fragments under one budget for the complete request;
   constructing an unbounded child string before truncating its parent would
   still expand that graph as a tree. The depth bound also covers types and
   recursive instance dictionaries. Small values retain the original format,
   while large values end in an explicit marker. Neither budget affects Rust
   serialization or the Thingol values being described. *)
local
  exception Debug_Limit;

  fun render emit value =
    let
      val remaining = Unsynchronized.ref 16384;
      val fragments = Unsynchronized.ref [];
      fun put s =
        if size s <= !remaining then
          (remaining := !remaining - size s;
           if s = "" then () else fragments := s :: !fragments)
        else
          (fragments := String.substring (s, 0, !remaining) :: !fragments;
           raise Debug_Limit);
      val _ = emit put 0 value
        handle Debug_Limit => fragments := "... <debug output truncated>" :: !fragments;
    in String.concat (rev (!fragments)) end;

  fun descend depth f =
    if depth >= 64 then raise Debug_Limit else f (depth + 1);

  fun delimited put left right emit xs =
    let
      fun items [] = ()
        | items [x] = emit x
        | items (x :: rest) = (emit x; put ", "; items rest);
    in put left; items xs; put right end;

  fun list put emit = delimited put "[" "]" emit;
  fun pair put emit_a emit_b (a, b) =
    (put "("; emit_a a; put ", "; emit_b b; put ")");

  fun typ put depth ty = descend depth (fn next =>
    case ty of
      ITyVar v => put v
    | v `%% tys => (put v; put "`%%"; list put (typ put next) tys));

  fun dict put depth (Dict (rels, plain)) = descend depth (fn next =>
    (put "Dict="; put "("; list put (pair put put put) rels; put ", ";
     plain_dict put next plain; put ")"))
  and plain_dict put depth d = descend depth (fn next =>
    case d of
      Dict_Const ((s, c), ds) =>
        (put "Dict_Const="; put "("; pair put put put (s, c); put ", ";
         list put (pair put (typ put next) (list put (dict put next))) ds; put ")")
    | Dict_Var {var, index, length, class, unique} =>
        (put "Dict_Var={var: "; put var; put ", index: "; put (Int.toString index);
         put ", length: "; put (Int.toString length); put ", class: "; put class;
         put ", unique: "; put (Bool.toString unique); put "}"));

  fun sym put _ s =
    (case s of
      Constant a => (put "Constant="; put a)
    | Type_Constructor a => (put "Type_Constructor="; put a)
    | Type_Class a => (put "Type_Class="; put a)
    | Class_Relation ab => (put "Class_Relation="; pair put put put ab)
    | Class_Instance ab => (put "Class_Instance="; pair put put put ab)
    | Module a => (put "Module"; put a));

  fun const put depth {sym = s, typargs, dicts, dom, range, annotation} =
    descend depth (fn next =>
      (put "{sym: "; sym put next s;
       put ", typargs: "; list put (typ put next) typargs;
       put ", dicts: "; list put (list put (dict put next)) dicts;
       put ", dom: "; list put (typ put next) dom;
       put ", range: "; typ put next range;
       put ", annotation: ";
       (case annotation of NONE => put "NONE" | SOME ty => typ put next ty);
       put "}"));

  fun vname NONE = "Anonymous"
    | vname (SOME v) = v;

  fun term put depth t = descend depth (fn next =>
    case t of
      IConst c => const put next c
    | IVar v => put (vname v)
    | a `$ b =>
        (put "("; term put next a; put "`$"; term put next b; put ")")
    | (v, ty1) `|=> (body, ty2) =>
        (put "("; pair put (put o vname) (typ put next) (v, ty1); put ", ";
         pair put (term put next) (typ put next) (body, ty2); put ")")
    | ICase {term = scrutinee, typ = ty, clauses, primitive = _} =>
        (put "{term: "; term put next scrutinee;
         put ", typ: "; typ put next ty;
         put ", clauses: "; list put (pair put (term put next) (term put next)) clauses;
         put ", primitive: <elided>}"));

  fun vars put vs = list put (pair put put (list put put)) vs;

  fun scheme put depth (vs, ty) =
    (put "("; vars put vs; put ", "; typ put depth ty; put ")");

  fun stmt put depth st = descend depth (fn next =>
    case st of
      Code_Thingol.NoStmt => put "NoStmt"
    | Code_Thingol.Fun ((sc, eqs), _) =>
        (put "Fun=(vs_ty="; scheme put next sc; put ", eqs=";
         list put (fn ((ts, body), _) =>
           (put "("; list put (term put next) ts; put ")=>"; term put next body)) eqs;
         put ")")
    | Code_Thingol.Datatype (vns, cos) =>
        (put "Datatype=("; list put put vns; put ", ";
         list put (pair put (pair put put (list put put)) (list put (typ put next))) cos;
         put ")")
    | Code_Thingol.Datatypecons v => (put "Datatypecons="; put v)
    | Code_Thingol.Class (c, (rels, params)) =>
        (put "Class=("; put c; put ", rels="; list put (pair put put put) rels;
         put ", params="; list put (pair put put (typ put next)) params; put ")")
    | Code_Thingol.Classrel rel => (put "Classrel="; pair put put put rel)
    | Code_Thingol.Classparam p => (put "Classparam="; put p)
    | Code_Thingol.Classinst {class, tyco, vs, ...} =>
        (put "Classinst={class: "; put class; put ", tyco: "; put tyco;
         put ", vs: "; vars put vs; put ", ...}"));

  fun node put depth ((s, st), children) =
    (put "{key: "; sym put depth s; put ", stmt: "; stmt put depth st;
     put ", children: "; list put (sym put depth) children; put "}");
in
  val print_debug_info_itype = render typ;
  val print_debug_info_dict = render dict;
  val print_plain_dict = render plain_dict;
  val print_debug_info_sym = render sym;
  val print_debug_info_const = render const;
  val dest_vname = vname;
  val print_debug_info_iterm = render term;
  val dest_typscheme = render scheme;
  val print_debug_info_thingol_stmt = render stmt;
  val print_debug_info_node = render node;
end

end
