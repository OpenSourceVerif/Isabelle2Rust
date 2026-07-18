(*  Title:      Tools/Code/code_rust.ML
    Serializer for Isabelle code generation to Rust.
*)

signature CODE_RUST =
sig
  val target: string
end;

structure Code_Rust : CODE_RUST =
struct

open Basic_Code_Symbol;     
open Basic_Code_Thingol;
open Code_Printer;

infixr 5 @@;
infixr 5 @|;


(** generic **)

val target = "Rust";

(** Intermediate binding representation: a single function definition. **)
datatype binding =
    Function of string * (typscheme * ((iterm list * iterm) * (thm option * bool)) list);

(** Intermediate statement IR: groups bindings into Rust-level declarations,
    produced from Code_Thingol stmts by modify_stmts before printing.
    Inst models a type-class instance as a Rust `impl Trait for Type { .. }`.
    Isabelle eliminates Classinst nodes (dictionary elimination) before the
    serializer runs, so instances are reconstructed from the specialized
    `<class>_<Type>_inst.<method>` projection functions: Inst carries (class,
    tyco), the instance type variables vs (for the impl generics/bounds), and
    one entry per trait method (classparam name + the implementing constant's
    symbol, whose body is inlined at print time). **)
datatype stmt =
    Exc of string * (typscheme * int)
  | Val of binding
  | Funs of (Code_Namespace.export * binding) list * Code_Symbol.T list
  | Datas of (string * (vname list * ((string * vname list) * itype list) list)) list
  | Class of string * (vname * ((class * class) list * (string * itype) list))
  | Inst of (class * string) * ((vname * sort) list * (string * Code_Symbol.T) list)
  (* A bundle of reconstructed impls emitted in a SINGLE statement slot.
     Code_Namespace.hierarchical_program requires modify_stmts to return no more
     entries than it received (code_namespace.ML:423 pads with a `replicate` that
     raises Subscript on a negative count). A datatype's missing superclass-closure
     impls are "extra" statements with no input sym of their own, so a small
     datatype group (e.g. single-constructor `RBT.rbt` needing two closures) would
     overflow. Packing every closure impl of a group into one InstGroup keeps the
     datatype group's output at two statements (Datas + InstGroup). *)
  | InstGroup of ((class * string) * ((vname * sort) list * (string * Code_Symbol.T) list)) list;

(** Print a product type (tuple), returning NONE for empty lists. **)
fun print_product _ [] = NONE
  | print_product print [x] = SOME (print x)
  | print_product print xs = (SOME o enum " *" "" "") (map print xs);

(** Print a tuple expression, wrapping multiple elements in parentheses. **)
fun tuplify _ _ [] = NONE
  | tuplify print fxy [x] = SOME (print fxy x)
  | tuplify print _ xs = SOME (enum "," "(" ")" (map (print NOBR) xs));

(** Join Pretty.T items with ", " using fixed spaces (no line breaks).
    Reprocesses Pretty.commas output to replace soft breaks with hard spaces. **)
fun commas_append prts = 
  let 
    fun combine (x1::x2::_::l) =
          Pretty.markup_open Markup.empty [x1, x2, str " "] :: combine l
      | combine [x] = [x]
      | combine [] = []
  in
    combine (Pretty.commas prts)
  end

(** Rust layout helpers.  They keep syntactic printers responsible for tokens
    and centralise only indentation / line breaking for braced Rust forms. **)
fun comma_lines [] = []
  | comma_lines [p] = [p]
  | comma_lines (p :: ps) = Pretty.block [p, str ","] :: comma_lines ps;

fun rust_indent prts = indent 4 (Pretty.chunks prts);

(* Concatenate layout fragments without making the current output column a new
   indentation baseline.  This matters for multiline expressions nested after
   tokens such as a dereference prefix, `((`, or `Constructor (`: their hard breaks
   should remain relative to the surrounding Rust block, not drift right by
   the width of every syntactic wrapper. *)
fun rust_open prts = Pretty.markup_open Markup.empty prts;

fun rust_open_chunks prts = rust_open (Pretty.fbreaks prts);

fun rust_parens prts =
  rust_open (str "(" :: commas_append prts @ [str ")"]);

fun rust_block header body =
  Pretty.chunks [Pretty.block [header, str " {"], rust_indent body, str "}"];

fun rust_bare_block body =
  rust_open_chunks [str "{", rust_indent body, str "}"];

fun rust_closure params return_type body =
  rust_open_chunks [
    Pretty.block
      (str "Rc::new(move |" :: params @ [str "|"] @ (case return_type of
          NONE => []
        | SOME typ => [str " -> ", typ]) @ [str " {"]),
    rust_indent [body],
    str "})"
  ];

fun rust_match scrutinee arms =
  rust_block (Pretty.block [str "match ", scrutinee]) (comma_lines arms);

fun rust_arm pat body =
  Pretty.chunks [Pretty.block [pat, str " =>"], rust_indent [body]];

fun rust_if cond then_body else_body =
  Pretty.chunks [
    Pretty.block [str "if ", cond, str " {"],
    rust_indent [then_body],
    str "} else {",
    rust_indent [else_body],
    str "}"
  ];

fun rust_where [] = []
  | rust_where bounds = [str "where", rust_indent (comma_lines bounds)];

fun rust_fn sig_head bounds body =
  if null bounds
  then rust_block sig_head body
  else Pretty.chunks ([sig_head] @ rust_where bounds @ [str "{", rust_indent body, str "}"]);

(** Convert CamelCase identifier to snake_case (for Rust function/variable names). **)
fun to_snake_case s =
  let
    val cs = String.explode s
    fun is_upper c = Char.isUpper c;
    fun is_lower c = Char.isLower c;
    fun aux [] = []
      | aux [c] = [Char.toLower c]
      | aux (c1 :: c2 :: cs) =
           if is_upper c1 andalso is_lower c2 then
             #"_" :: Char.toLower c1 :: aux (c2 :: cs)
           else if is_upper c1 andalso is_upper c2 then
             Char.toLower c1 :: aux (c2 :: cs)
           else
             Char.toLower c1 :: aux (c2 :: cs)
    fun auxx [] = []
      | auxx [c] = [Char.toLower c]
      | auxx (c :: cs) = Char.toLower c :: aux cs
  in String.implode (auxx cs) end;

(** Convert snake_case identifier to UpperCamelCase (for Rust type/enum names). **)
fun to_upper_camel_case s =
  let
    val cs = String.explode s
    fun aux [] = []
      | aux [c] = [c]
      | aux (c1 :: c2 :: cs) =
        if (c1 = #"_") then Char.toUpper c2 :: aux cs
        else c1 :: aux (c2 :: cs)
    fun auxx [] = []
      | auxx [c] = [Char.toUpper c]
      | auxx (c :: cs) = Char.toUpper c :: aux cs
  in String.implode (auxx cs) end;

(** Rust serializer **)

(** Escape a string into a valid Rust string literal. **)
val print_rust_string =
  let
    fun unicode i = "\\u{" ^ Int.toString i ^ "}"
    fun char "\"" = "\\\""
      | char "\\" = "\\\\"
      | char c =
         let val i = ord c
         in if i < 32 orelse i > 126
          then unicode i
          else if i >= 128
          then error "non-ASCII byte in Rust string literal"
          else c
        end;
  in quote o translate_string char end;

(** Extract parameter and return types from a function itype as a flat list.
    e.g. fun(A, fun(B, C)) -> [A, B, C] **)
fun extract_typ print_typ ("fun"`%%[ty1, ty2]) = 
  print_typ (INFX (1, X)) ty1
  :: (case ty2 
    of fs as ("fun"`%%[_, _]) => extract_typ print_typ fs
    | _ => [print_typ (INFX (1, X)) ty2])
  | extract_typ print_typ ty = [print_typ (INFX (1, X)) ty]

(** Render a HOL function type as the cloneable trait object
    `Rc<dyn Fn(params) -> ret>`. Used both for the `fun` type-constructor syntax
    and for a function definition whose Rust signature returns a function, so the
    two stay identical. `Rc` (not `Box`) because every datatype derives Clone and
    the backend emits `+ Clone` bounds; `Rc<dyn Fn>` is Clone but `Box<dyn Fn>` is
    not (E0277). The default object lifetime is `'static`, which holds for the
    `move` closures we emit (they capture owned clones). **)
fun rc_dyn_fn params ret =
  Pretty.block (
    str "Rc<dyn Fn"
    :: enum "," "(" ")" params
    :: str " -> "
    :: ret
    :: [str ">"]
  )

(** Main statement printer: given syntaxes and lookup functions, returns print_stmt.
    Contains all local printers for types, terms, patterns, cases, defs, and stmts.
    Parameters:
      tyco_syntax/const_syntax: user-registered custom syntax overrides
      reserved: reserved name context
      is_constr: test if a symbol is a constructor
      deresolve: resolve qualified symbol to its printed Rust name
      box_table: precomputed map from a data constructor to a bool list (one per
        field) saying which fields need Box<> indirection (used both for the enum
        declaration and for construction/pattern term printing)
      lookup_constant_typeco: look up which type constructor a constant belongs to
      lookup_constructor_fields: look up a constructor's polymorphic result
        parameters and field types, used to propagate an expected type into fields
      is_single_constr: true if a data constructor is the only constructor of its datatype
      lookup_constant_fun: look up the exact definition of
      lookup_method_class: SOME class if the symbol is a class parameter (trait
        method), NONE otherwise
      inst_method_info: SOME (tyco, classparam) if the symbol is a reconstructed
        instance method living in an `impl` block, NONE otherwise
      constr_method_of: SOME constructor-sym if (classparam, tyco) is a class
        method realised by a nullary data constructor (e.g. `0::int`), so the
        Inst printer fills its body with the constructor instead of a panic stub **)
fun print_rust_stmt tyco_syntax const_syntax reserved is_constr deresolve
  box_table phantom_table
  lookup_constant_typeco lookup_constructor_fields is_single_constr lookup_constant_fun
  lookup_method_class inst_method_info lookup_class_methods constr_method_of =
  let
    val deresolve_const = deresolve o Constant;
    val deresolve_typco = deresolve o Type_Constructor;
    val deresolve_class = deresolve o Type_Class;
    (** The bare base name of a symbol (last path segment of its possibly
        crate-qualified deresolved name). Used in Rust "suffix" positions that
        must stay unqualified -- enum variants after `Enum::` and trait methods
        after `Type::` -- where the qualified path is carried by the prefix. **)
    fun deresolve_base sym = List.last (String.fields (fn c => c = #":") (deresolve sym));
    fun box p = Pretty.block [str "Box<", p, str ">"]
    fun clone p = Pretty.block [p, str ".clone()"]
    fun box_new p = Pretty.block [str "Box::new(", p, str ")"]
    fun box_pattern p = Pretty.block [str "box ", p]
    fun to_upper s = (String.implode (map Char.toUpper (String.explode s)))
    (** Print a type constructor application `Tyco<args>`. Box<> wrapping of a
        recursive datatype field is applied by print_datatype_decl from the
        precomputed box_table, so type printing itself is box-agnostic. **)
    fun print_tyco_expr_gen (sym, tys) =
      let
        val tyconame = deresolve sym
      in
        (case tys
        of [] => str tyconame
        | _ =>
          Pretty.block(
            str tyconame
            :: str "<"
            :: enum "," "" "" (map (print_typ_gen BR) tys)
            :: [str ">"]
          ))
      end
    (** Print an itype to Rust type syntax.
        Dispatches to custom tyco_syntax or default print_tyco_expr_gen. **)
    and print_typ_gen fxy (tyco `%% tys) = (case tyco_syntax tyco
         of NONE => print_tyco_expr_gen (Type_Constructor tyco, tys)
          | SOME (_, print) => print print_typ_gen fxy tys)
      | print_typ_gen _ (ITyVar v) =
        (* "Self" is a sentinel injected by print_trait_typ for a class's own type
           variable; keep it verbatim (Rust keyword), uppercase everything else. *)
        if v = "Self" then str "Self" else str (to_upper v);
    (* A type constructor must honour user code_printing (tyco_syntax) here too,
       not only in print_typ_gen: an instance header `impl Class for Tyco` prints
       its `Tyco` through this function, and a code_printing-mapped type (e.g.
       int/nat -> BigInt) has no program node, so a bare deresolve would raise
       "Unknown statement name". Route Type_Constructor through print_typ_gen
       (which dispatches on tyco_syntax); other symbols (classes) deresolve. *)
    fun print_tyco_expr (Type_Constructor t, tys) = print_typ_gen NOBR (t `%% tys)
      | print_tyco_expr (sym, tys) = print_tyco_expr_gen (sym, tys);
    (* The printed name of a type constructor for use as a path prefix
       (`Tyco::method`) or enum qualifier (`Tyco::Variant`). A code_printing-mapped
       type (e.g. int/nat -> BigInt) has no program node, so deresolve would raise
       "Unknown statement name"; fall back to its tyco_syntax rendering. *)
    fun tyco_name_str t =
      (case tyco_syntax t of
          SOME (_, pr) => Pretty.unformatted_string_of (pr print_typ_gen NOBR [])
        | NONE => deresolve (Type_Constructor t));
    fun print_typ fxy ty = print_typ_gen fxy ty;
    fun print_dicttyp (class, ty) = print_tyco_expr (Type_Class class, []); (*omit generic param Self*)
    (** Print a method signature "fn name(x0: T0, ..) -> Ret <tail>", with the
        class's own type variable `self_var` replaced by the sentinel "Self"
        everywhere it occurs — including NESTED positions such as the `'a` of
        `'a itself` in `len_of :: 'a itself => nat`, which must print as
        `Itself<Self>`, not `Itself<A>` (A is unbound in the trait). `tail` is the
        suffix after the return type: a trait declaration uses
        " where Self: Sized;"; an inlined/stub method body uses " { .. }". **)
    fun print_method_sig method_name ty self_var tail =
      let
        fun subst_self (ITyVar u) = ITyVar (if u = self_var then "Self" else u)
          | subst_self (tyco `%% tys) = tyco `%% map subst_self tys
        val ts = extract_typ print_typ (subst_self ty)
        val param_num = (List.length ts) - 1
        val ret_typ = List.last ts
        val param_typs = List.take (ts, param_num)
        val dummy_params = List.tabulate (param_num, fn i => "x" ^ Int.toString i)
        val params = map (fn (s, p) => Pretty.block[str (s^": "), p])
          (ListPair.zip (dummy_params, param_typs))
      in
        Pretty.block(
          str "fn "
          :: str method_name
          :: enum "," " (" ")" params
          :: str " -> "
          :: ret_typ
          :: tail
        )
      end;
    (* `where Self: Sized`: in a trait, Self is implicitly `?Sized`. Rust adds
       this bound automatically for a method taking Self DIRECTLY by value, but
       not when Self is nested in another by-value type such as `Itself<Self>`
       (len_of), which then fails E0277. All our instances are sized, so make the
       bound explicit on every trait method declaration. *)
    fun print_trait_typ class ty self_var =
      print_method_sig (deresolve_const class) ty self_var [str " where Self: Sized;"];
    (** Print type scheme prefix: where-clause with trait bounds from sort annotations. **)
    fun print_typscheme_prefix (vs, p) = enum " ->" "" ""
      (map_filter (fn (v, sort) =>
        (print_product (fn class => print_dicttyp (class, ITyVar v)) sort)) vs @| p);
    fun print_typscheme (vs, ty) = print_typscheme_prefix (vs, print_typ NOBR ty);
    (** Print the generic parameter list with trait bounds for an `impl` header,
        e.g. <A : Clone + Semigroup, B : Clone + Semigroup>, from the instance's
        type variables and their sort (superclass) constraints. **)
    fun print_impl_generics vs =
      if List.null vs then str ""
      else
        let
          fun print_vs_trait (vname, sort) =
            Pretty.block (
              str ((to_upper vname)^" : Clone")
              :: (if List.null sort then []
                  else [enum " +" " + " "" (map (fn s => print_tyco_expr (Type_Class s, [])) sort)])
              (* `'static` to match the function bound printer: impl methods call
                 free functions (e.g. power) that require it, and our closures are
                 `Rc<dyn Fn + 'static>` capturing owned clones (E0310). *)
              @ [str " + 'static"])
        in enum "" "<" ">" (commas_append (map print_vs_trait vs)) end;

    fun fun_typs ("fun"`%%[ty1, ty2]) =
          let val (tys, ret) = fun_typs ty2 in (ty1 :: tys, ret) end
      | fun_typs ty = ([], ty);
    fun arrow_arity ("fun"`%%[_, ty2]) = 1 + arrow_arity ty2
      | arrow_arity _ = 0;
    fun mk_fun_ty ([], ret) = ret
      | mk_fun_ty (ty :: tys, ret) = "fun"`%%[ty, mk_fun_ty (tys, ret)];
    (** A HOL itype does not record how its adjacent arrows are grouped into Rust
        trait objects: both `Fn(A, B) -> C` and `Fn(A) -> Fn(B) -> C` erase to
        `A => B => C`.  Keep that representation choice alongside the semantic
        type while printing terms.  Ordinary concrete function types use one
        flat Rust_Fn group; nested groups arise only where a polymorphic result
        variable is itself instantiated by a function in an enclosing context. **)
    datatype rust_shape =
        Rust_Var of string
      | Rust_Tyco of string * rust_shape list
      | Rust_Fn of rust_shape list * rust_shape;
    type expected_type = {hol_type: itype, rust_shape: rust_shape};
    fun shape_type (Rust_Var v) = ITyVar v
      | shape_type (Rust_Tyco (tyco, shapes)) = tyco `%% map shape_type shapes
      | shape_type (Rust_Fn (args, ret)) =
          mk_fun_ty (map shape_type args, shape_type ret);
    fun default_rust_shape (ITyVar v) = Rust_Var v
      | default_rust_shape (ty as ("fun" `%% [_, _])) =
          let val (args, ret) = fun_typs ty
          in Rust_Fn (map default_rust_shape args, default_rust_shape ret) end
      | default_rust_shape (tyco `%% tys) =
          Rust_Tyco (tyco, map default_rust_shape tys);
    (** Print every level of a selected representation shape.  Falling back to
        `print_typ (shape_type shape)` for a non-function outer constructor would
        erase non-default function groupings in its arguments, for example turning
        `Set<Rc<dyn Fn(A) -> Fn(B)>>` back into `Set<Rc<dyn Fn(A, B)>>`.

        Registered type syntax still owns the outer spelling.  Feed it distinct
        placeholder type variables and resolve each placeholder with the matching
        child shape, so positional syntaxes such as native Rust tuples retain both
        their existing layout and each argument's independent representation. **)
    fun print_rust_shape (Rust_Fn (args, ret)) =
          rc_dyn_fn (map print_rust_shape args) (print_rust_shape ret)
      | print_rust_shape (Rust_Tyco (tyco, shapes)) =
          (case tyco_syntax tyco of
            NONE =>
              (case shapes of
                [] => str (deresolve_typco tyco)
              | _ => Pretty.block
                  (str (deresolve_typco tyco) :: str "<"
                    :: enum "," "" "" (map print_rust_shape shapes)
                    :: [str ">"]))
          | SOME (_, print) =>
              let
                val placeholders = map_index (fn (i, _) =>
                  "__rust_shape_" ^ Int.toString i) shapes;
                val placeholder_shapes = ListPair.zip (placeholders, shapes);
                fun print_placeholder fxy (ITyVar v) =
                      (case AList.lookup (op =) placeholder_shapes v of
                        SOME shape => print_rust_shape shape
                      | NONE => print_typ_gen fxy (ITyVar v))
                  | print_placeholder fxy ty = print_typ_gen fxy ty;
              in
                print print_placeholder NOBR (map ITyVar placeholders)
              end)
      | print_rust_shape (Rust_Var v) = print_typ NOBR (ITyVar v);
    fun rust_shape_groups (Rust_Fn (args, ret)) =
          length args :: rust_shape_groups ret
      | rust_shape_groups _ = [];
    (** Variable bindings retain both their semantic HOL type and their selected
        Rust representation.  A lambda parameter introduced at a dictionary
        boundary may be a nested unary function even though its itype is the same
        arrow chain as an ordinary flat parameter; later uses and applications of
        that variable must not discard this distinction. **)
    type rust_var_ctxt =
      Code_Printer.var_ctxt * (itype * rust_shape) Symtab.table;
    fun rv_names (vars: rust_var_ctxt) = #1 vars;
    fun rv_types (vars: rust_var_ctxt) = #2 vars;
    fun rv_intro_base_names_for no_syntax deresolve ts (vars: rust_var_ctxt) =
      (intro_base_names_for no_syntax deresolve ts (rv_names vars), rv_types vars);
    fun rv_lookup_var vars v = lookup_var (rv_names vars) v;
    fun rv_lookup_type vars v = Option.map fst (Symtab.lookup (rv_types vars) v);
    fun rv_lookup_shape vars v = Option.map snd (Symtab.lookup (rv_types vars) v);
    fun rv_intro_typed_pat_shape pat ty shape (vars: rust_var_ctxt) =
      let
        val vs = build (Code_Thingol.add_varnames pat);
        val names' = intro_vars vs (rv_names vars);
        val tys' =
          let
            fun add_pat_ty t ty shape =
              (case t of
                IVar (SOME v) => Symtab.update (v, (ty, shape))
              | IVar NONE => I
              | _ =>
                  (case Code_Thingol.unfold_const_app t of
                    SOME ({dom, ...}, ts) =>
                      if length dom = length ts
                      then fold (fn (t, field_ty) =>
                        add_pat_ty t field_ty (default_rust_shape field_ty))
                        (ListPair.zip (ts, dom))
                      else fold (fn v => Symtab.update
                        (v, (ty, default_rust_shape ty))) vs
                  | NONE => fold (fn v => Symtab.update
                      (v, (ty, default_rust_shape ty))) vs))
          in add_pat_ty pat ty shape (rv_types vars) end
      in (names', tys') end;
    fun rv_intro_typed_pat pat ty vars =
      rv_intro_typed_pat_shape pat ty (default_rust_shape ty) vars;
    fun rv_intro_typed_pats pats_tys vars =
      fold (fn (pat, ty) => rv_intro_typed_pat pat ty) pats_tys vars;
    fun term_type vars (IConst {dom, range, ...}) = SOME (mk_fun_ty (dom, range))
      | term_type vars (IVar (SOME v)) = rv_lookup_type vars v
      | term_type _ (IVar NONE) = NONE
      | term_type vars (t1 `$ _) =
          (case term_type vars t1 of
            SOME ("fun"`%%[_, ty2]) => SOME ty2
          | _ => NONE)
      | term_type vars ((_, ty) `|=> (_, rty)) = SOME ("fun"`%%[ty, rty])
      | term_type vars (ICase {clauses = (_, body) :: _, ...}) = term_type vars body
      | term_type _ (ICase {clauses = [], ...}) = NONE;
    fun add_default_shape_subst (ITyVar v) inst subst =
          if AList.defined (op =) subst v then subst
          else (v, default_rust_shape inst) :: subst
      | add_default_shape_subst (decl_tyco `%% decl_tys)
          (inst_tyco `%% inst_tys) subst =
          if decl_tyco = inst_tyco andalso length decl_tys = length inst_tys
          then fold (fn (decl, inst) => add_default_shape_subst decl inst)
            (ListPair.zip (decl_tys, inst_tys)) subst
          else subst
      | add_default_shape_subst _ _ subst = subst;
    (** Match an enclosing representation against a declaration result.  A type
        variable receives the complete contextual shape, rather than merely its
        erased itype; this is what lets successive applications of a polymorphic
        one-step operator accumulate `[A][B][C]` instead of stopping at
        `[A][B,C]`. **)
    fun bind_expected_shape (ITyVar v) shape subst =
          AList.update (op =) (v, shape) subst
      | bind_expected_shape (decl as ("fun" `%% [_, _]))
          (Rust_Fn (arg_shapes, ret_shape)) subst =
          let val (decl_args, decl_ret) = fun_typs decl
          in
            if length decl_args = length arg_shapes
            then subst
              |> fold (fn (decl_arg, arg_shape) =>
                   bind_expected_shape decl_arg arg_shape)
                   (ListPair.zip (decl_args, arg_shapes))
              |> bind_expected_shape decl_ret ret_shape
            else subst
          end
      | bind_expected_shape (decl_tyco `%% decl_tys)
          (Rust_Tyco (shape_tyco, arg_shapes)) subst =
          if decl_tyco = shape_tyco andalso length decl_tys = length arg_shapes
          then fold (fn (decl, shape) => bind_expected_shape decl shape)
            (ListPair.zip (decl_tys, arg_shapes)) subst
          else subst
      | bind_expected_shape _ _ subst = subst;
    (** Instantiate a declaration template with both its concrete HOL types and
        the contextual shapes already bound for result variables.  All adjacent
        arrows explicitly written in the template remain one Rust_Fn parameter
        group; a bound result-variable shape becomes the returned group tree. **)
    fun instantiate_rust_shape subst (ITyVar v) inst =
          (case AList.lookup (op =) subst v of
            SOME shape => shape
          | NONE => default_rust_shape inst)
      | instantiate_rust_shape subst (decl as ("fun" `%% [_, _])) inst =
          let
            val (decl_args, decl_ret) = fun_typs decl;
            val (inst_args, inst_ret) = fun_typs inst;
            val explicit = length decl_args;
          in
            if explicit > 0 andalso length inst_args >= explicit
            then
              let
                val inst_explicit = take explicit inst_args;
                val inst_tail = mk_fun_ty (drop explicit inst_args, inst_ret);
              in
                Rust_Fn
                  (map2 (instantiate_rust_shape subst) decl_args inst_explicit,
                   instantiate_rust_shape subst decl_ret inst_tail)
              end
            else default_rust_shape inst
          end
      | instantiate_rust_shape subst (decl_tyco `%% decl_tys)
          (inst_tyco `%% inst_tys) =
          if decl_tyco = inst_tyco andalso length decl_tys = length inst_tys
          then Rust_Tyco (inst_tyco,
            map2 (instantiate_rust_shape subst) decl_tys inst_tys)
          else default_rust_shape (inst_tyco `%% inst_tys)
      | instantiate_rust_shape _ _ inst = default_rust_shape inst;
    fun expected_from subst decl inst =
      SOME {hol_type = inst, rust_shape = instantiate_rust_shape subst decl inst};
    (** Derive each argument's Rust representation.  Besides declaration and
        instantiation types, an ordinary function now consumes the expected
        representation of its result.  Matching that result back to declaration
        variables makes the representation flow through nested calls, datatype
        fields and native tuple syntax without naming a particular constant such
        as Code_Evaluation.valapp. **)
    fun argument_expecteds expected sym dom range =
      let
        fun pad xs =
          if length xs = length dom then xs else replicate (length dom) NONE;
        fun constructor_expecteds (parent, vs, fields) =
          if length fields = length dom
          then
            let
              val decl_result = parent `%% map ITyVar vs;
              val subst0 = add_default_shape_subst decl_result range [];
              val subst =
                (case expected of
                  SOME {rust_shape, ...} =>
                    bind_expected_shape decl_result rust_shape subst0
                | NONE => subst0);
            in map2 (expected_from subst) fields dom end
          else replicate (length dom) NONE;
        fun function_expecteds () =
          (case lookup_constant_fun sym of
            SOME (((_, decl_ty), _), _) =>
              let
                val inst_ty = mk_fun_ty (dom, range);
                val subst0 = add_default_shape_subst decl_ty inst_ty [];
                val (decl_args, decl_ret) = fun_typs decl_ty;
                val subst =
                  (case expected of
                    SOME {rust_shape, ...} =>
                      bind_expected_shape decl_ret rust_shape subst0
                  | NONE => subst0);
                val n = Int.min (length decl_args, length dom);
              in
                map2 (expected_from subst)
                  (take n decl_args) (take n dom)
                @ replicate (Int.max (0, length dom - length decl_args)) NONE
              end
          | NONE => replicate (length dom) NONE);
        (* Some code_printing primitives (notably Product_Type.Pair rendered by
           native tuple syntax) have no surviving Datatypecons node.  When their
           instantiated result arguments are exactly their term domains, project
           the caller's expected result arguments positionally into those terms. *)
        fun syntax_result_expecteds {rust_shape, ...} =
          (case (rust_shape, range) of
            (Rust_Tyco (shape_tyco, arg_shapes), inst_tyco `%% inst_args) =>
              if shape_tyco = inst_tyco andalso length arg_shapes = length dom
                  andalso length inst_args = length dom
                  andalso ListPair.allEq (op =) (dom, inst_args)
              then map2 (fn shape => fn ty =>
                SOME {hol_type = ty, rust_shape = shape}) arg_shapes dom
              else replicate (length dom) NONE
          | _ => replicate (length dom) NONE);
        val result = pad (case lookup_constructor_fields sym of
          SOME constructor =>
            (case expected of SOME _ => constructor_expecteds constructor
             | NONE => replicate (length dom) NONE)
        | NONE =>
            (case (lookup_constant_fun sym, expected) of
              (NONE, SOME exp) => syntax_result_expecteds exp
            | _ => function_expecteds ()));
      in result end;
    fun classparam_decl cp =
      (case lookup_method_class (Constant cp) of
        SOME class =>
          (case lookup_class_methods class of
            SOME (self_var, cps) =>
              Option.map (fn mty => (class, self_var, mty)) (AList.lookup (op =) cps cp)
          | NONE => NONE)
      | NONE => NONE);
    fun classparam_arrow_arity cp =
      Option.map (fn (_, _, mty) => arrow_arity mty) (classparam_decl cp);
    fun trait_method_arity sym =
      (case inst_method_info sym of
        SOME (_, cp) => classparam_arrow_arity cp
      | NONE =>
          (case sym of
            Constant cp => classparam_arrow_arity cp
          | _ => NONE));
    (** Reconstruct the Rust representation selected by a type-class dictionary.
        A dictionary for an instance at HOL `fun` contains the domain evidence
        and, recursively, the codomain evidence.  That recursive instance path is
        represented in Rust by nested unary trait objects
        `Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> C>>`, even though the same erased itype
        would ordinarily print as the flat `Rc<dyn Fn(A, B) -> C>`.  Non-function
        instances retain their ordinary type-constructor shape. **)
    fun dictionary_rust_shape (Code_Thingol.Dict (_, plain)) =
          plain_dictionary_rust_shape plain
    and plain_dictionary_rust_shape
          (Code_Thingol.Dict_Const ((tyco, _), dss)) =
          let
            val arg_shapes = map (fn (ty, ds) =>
              dictionary_argument_shape ty ds) dss;
          in
            SOME (case (tyco, arg_shapes) of
              ("fun", [arg_shape, result_shape]) =>
                Rust_Fn ([arg_shape], result_shape)
            | _ => Rust_Tyco (tyco, arg_shapes))
          end
      | plain_dictionary_rust_shape
          (Code_Thingol.Dict_Var {var, ...}) = SOME (Rust_Var var)
    and dictionary_argument_shape ty ds =
          (case get_first (fn dict =>
              (case dictionary_rust_shape dict of
                SOME shape =>
                  if shape_type shape = ty then SOME shape else NONE
              | NONE => NONE)) ds of
            SOME shape => shape
          | NONE => default_rust_shape ty);
    fun trait_classparam sym =
      (case inst_method_info sym of
        SOME (_, cp) => SOME cp
      | NONE => (case sym of Constant cp => SOME cp | _ => NONE));
    fun match_class_self self_var (ITyVar v) inst =
          if v = self_var then SOME inst else NONE
      | match_class_self self_var (decl_tyco `%% decl_tys)
          (inst_tyco `%% inst_tys) =
          if decl_tyco = inst_tyco andalso length decl_tys = length inst_tys
          then get_first (fn (decl, inst) =>
            match_class_self self_var decl inst)
            (ListPair.zip (decl_tys, inst_tys))
          else NONE
      | match_class_self _ _ _ = NONE;
    (** Recover the semantic Self type of a class-method occurrence.  Self may
        occur inside a method argument such as `Set<Self>` or `Itself<Self>`, so
        it is found by structural matching rather than by selecting the first
        term argument. **)
    fun trait_receiver_type
        (const as {sym, dom, range, ...}: Code_Thingol.const) =
      let
        val instantiated_ty = mk_fun_ty (dom, range);
        val inferred_self =
          (case trait_classparam sym of
            SOME cp =>
              (case classparam_decl cp of
                SOME (_, self_var, method_ty) =>
                  match_class_self self_var method_ty instantiated_ty
              | NONE => NONE)
          | NONE => NONE);
        val wanted = the_default (length dom) (trait_method_arity sym);
      in
        (case inferred_self of
          SOME self_ty => self_ty
        | NONE =>
            (* Retain the legacy fallback for an incomplete class declaration in
               a partial export. *)
            if is_some (inst_method_info sym) andalso wanted = 0
            then instantiated_ty
            else if null dom then range else hd dom)
      end;
    fun typearg_dictionary_shape
        ({typargs, dicts, ...}: Code_Thingol.const) ty =
      if length typargs <> length dicts then NONE
      else get_first (fn (inst_ty, ds) =>
        if inst_ty <> ty then NONE
        else get_first (fn dict =>
          (case dictionary_rust_shape dict of
            SOME shape =>
              if shape_type shape = ty then SOME shape else NONE
          | NONE => NONE)) ds)
        (ListPair.zip (typargs, dicts));
    (** Ordinary dictionary-eliminated wrappers such as `HOL.eq` remain plain
        polymorphic Rust functions, but a function-typed generic argument must
        still use the representation selected by its instance dictionary.  When
        an instantiated domain is exactly one of the wrapper's type arguments,
        prefer that dictionary shape over the erased itype-derived expectation;
        this lets Rust infer the wrapper parameter as recursively unary Self
        instead of the flat function trait object for which no impl exists. **)
    fun dictionary_argument_expecteds expected
        (const as {sym, dom, range, ...}: Code_Thingol.const) =
      let
        val base = argument_expecteds expected sym dom range;
        fun enrich_shape shape =
          (case typearg_dictionary_shape const (shape_type shape) of
            SOME evidenced => evidenced
          | NONE =>
              (case shape of
                Rust_Fn (args, result) =>
                  Rust_Fn (map enrich_shape args, enrich_shape result)
              | Rust_Tyco (tyco, args) =>
                  Rust_Tyco (tyco, map enrich_shape args)
              | Rust_Var _ => shape));
        fun enrich ty fallback =
          let
            val original =
              (case fallback of
                SOME {rust_shape, ...} => rust_shape
              | NONE => default_rust_shape ty);
            val enriched = enrich_shape original;
          in
            if is_none fallback andalso enriched = original then NONE
            else SOME {hol_type = ty, rust_shape = enriched}
          end;
      in map2 enrich dom base end;
    (** Recover the Rust Self shape selected at a trait call.  Reconstructed
        instance methods expose dictionaries for the instance type parameters,
        rather than one dictionary for the complete Self type, so rebuild the
        outer instance constructor and enrich each parameter from its evidence.
        A direct class-parameter call instead carries evidence for Self itself. **)
    fun trait_receiver_shape (const as {sym, ...}: Code_Thingol.const) =
      let
        val self_ty = trait_receiver_type const;
        fun argument_shape ty =
          the_default (default_rust_shape ty)
            (typearg_dictionary_shape const ty);
        fun instance_shape tyco tys =
          let val shapes = map argument_shape tys in
            (case (tyco, shapes) of
              ("fun", [arg_shape, result_shape]) =>
                Rust_Fn ([arg_shape], result_shape)
            | _ => Rust_Tyco (tyco, shapes))
          end;
      in
        (case inst_method_info sym of
          SOME (tyco, _) =>
            (case self_ty of
              self_tyco `%% tys =>
                if self_tyco = tyco then instance_shape tyco tys
                else default_rust_shape self_ty
            | _ => default_rust_shape self_ty)
        | NONE =>
            the_default (default_rust_shape self_ty)
              (typearg_dictionary_shape const self_ty))
      end;
    (** Instantiate the class parameter's declared result with the dictionary-
        selected Self shape.  For a method such as `inf :: Self -> Self -> Self`
        on binary relations, this makes both the call result and any subsequent
        applications follow `[A][B]`, matching the recursively reconstructed
        pointwise function impl. **)
    fun trait_result_shape (const as {sym, dom, range, ...}: Code_Thingol.const) =
      (case trait_classparam sym of
        SOME cp =>
          (case classparam_decl cp of
            SOME (_, self_var, method_ty) =>
              let
                val instantiated_ty = mk_fun_ty (dom, range);
                val (_, declared_result) = fun_typs method_ty;
                val subst =
                  add_default_shape_subst method_ty instantiated_ty []
                  |> bind_expected_shape (ITyVar self_var)
                       (trait_receiver_shape const);
              in SOME (instantiate_rust_shape subst declared_result range) end
          | NONE => NONE)
      | NONE => NONE);
    fun rust_shape_argument_expecteds (Rust_Fn (args, result)) =
          map (fn shape => SOME {hol_type = shape_type shape,
            rust_shape = shape}) args
          @ rust_shape_argument_expecteds result
      | rust_shape_argument_expecteds _ = [];
    (** Expected representations for a trait call are governed by the class
        parameter, not by every arrow of the implementing pointwise equation.
        The first prefix is the trait method's declared arguments with Self bound
        to the dictionary-selected shape; any remaining term arguments apply the
        method's function-valued result group by group. **)
    fun trait_argument_expecteds
        (const as {sym, dom, ...}: Code_Thingol.const) =
      (case (trait_classparam sym, trait_method_arity sym,
          trait_result_shape const) of
        (SOME cp, SOME wanted, SOME result_shape) =>
          (case classparam_decl cp of
            SOME (_, self_var, method_ty) =>
              let
                val (declared_args, _) = fun_typs method_ty;
                val method_dom = take (Int.min (wanted, length dom)) dom;
                val instantiated_method_ty =
                  mk_fun_ty (method_dom, shape_type result_shape);
                val subst =
                  add_default_shape_subst method_ty instantiated_method_ty []
                  |> bind_expected_shape (ITyVar self_var)
                       (trait_receiver_shape const);
                val n = Int.min (length declared_args, length method_dom);
                val method_expecteds =
                  map2 (expected_from subst)
                    (take n declared_args) (take n method_dom)
                  @ replicate (Int.max (0, wanted - n)) NONE;
                val result_expecteds =
                  rust_shape_argument_expecteds result_shape;
                val extra = Int.max (0, length dom - wanted);
              in method_expecteds
                @ take (Int.min (extra, length result_expecteds)) result_expecteds
                @ replicate (Int.max (0, extra - length result_expecteds)) NONE
              end
          | NONE => argument_expecteds NONE sym dom (#range const))
      | _ => argument_expecteds NONE sym dom (#range const));
    fun drop_shape_arguments 0 shape = shape
      | drop_shape_arguments n (Rust_Fn (args, result)) =
          if n < length args
          then Rust_Fn (drop n args, result)
          else drop_shape_arguments (n - length args) result
      | drop_shape_arguments _ shape = shape;
    fun drop_fun_type 0 ty = ty
      | drop_fun_type n ("fun" `%% [_, result]) =
          drop_fun_type (n - 1) result
      | drop_fun_type _ ty = ty;
    (** The executable equations, rather than the fully instantiated occurrence
        type, determine how many arguments an ordinary Rust function item accepts.
        Keep this calculation shared by call printing and result-shape recovery:
        any remaining arrows belong to the returned function value. **)
    fun ordinary_function_arity sym fallback =
      (case lookup_constant_fun sym of
        SOME (((vs, ty), raw_eqs), _) =>
          let val eqs = filter (snd o snd) raw_eqs in
            (case eqs of
              [] => arrow_arity ty
            | [(([], _), _)] =>
                if null (filter_out (null o snd) vs)
                    andalso (not o null o fst o Code_Thingol.unfold_fun) ty
                then 1
                else 0
            | _ => length (hd (map (fst o fst) eqs)))
          end
      | NONE => fallback);
    fun substitute_rust_shape subst (Rust_Var v) =
          the_default (Rust_Var v) (AList.lookup (op =) subst v)
      | substitute_rust_shape subst (Rust_Tyco (tyco, shapes)) =
          Rust_Tyco (tyco, map (substitute_rust_shape subst) shapes)
      | substitute_rust_shape subst (Rust_Fn (args, result)) =
          Rust_Fn (map (substitute_rust_shape subst) args,
            substitute_rust_shape subst result);
    (** Instantiate a function declaration's type variables with the concrete
        call occurrence and then refine those substitutions from its dictionaries.
        In particular, a variable instantiated by a multi-arrow HOL function may
        be represented by the recursive unary shape selected by its class instance. **)
    fun dictionary_shape_subst
        (const: Code_Thingol.const) decl_ty inst_ty =
      add_default_shape_subst decl_ty inst_ty []
      |> map (fn (v, shape) =>
          (v, the_default shape
            (typearg_dictionary_shape const (shape_type shape))));
    (** Source representation of a saturated trait call, used before an
        enclosing expected type is applied.  Extra HOL applications consume the
        returned function according to its dictionary-selected Rust groups. **)
    fun trait_term_rust_shape t =
      (case Code_Thingol.unfold_const_app t of
        SOME (const as {sym, ...}, ts) =>
          (case trait_method_arity sym of
            SOME wanted =>
              if length ts < wanted then NONE
              else Option.map
                (drop_shape_arguments (length ts - wanted))
                (trait_result_shape const)
          | NONE => NONE)
      | NONE => NONE);
    (** Recover the representation produced by an ordinary polymorphic call.
        Rust traits attach dictionary evidence to the concrete type used for a
        declaration variable.  That evidence affects occurrences of the variable
        in the result as well as in arguments: `collect :: (A => bool) => Set<A>`
        called at a function-valued A therefore produces `Set<nested-Fn>`, not the
        same container with the backend's unrelated default flat Fn spelling.

        A callee whose own equations already selected a non-default result shape
        contributes that shape as the declaration template.  The `seen` guard
        makes mutually recursive definitions fall back to their ordinary declared
        representation instead of recursively inspecting bodies forever. **)
    fun selected_term_rust_shape_seen seen vars t =
      let val (callee, args) = Code_Thingol.unfold_app t in
        (case callee of
          IVar (SOME v) => Option.map
            (drop_shape_arguments (length args)) (rv_lookup_shape vars v)
        | IConst const =>
            (case trait_term_rust_shape t of
              SOME shape => SOME shape
            | NONE => ordinary_term_rust_shape seen const args)
        | _ => trait_term_rust_shape t)
      end
    and ordinary_term_rust_shape seen
        (const as {sym, dom, range, ...}: Code_Thingol.const) args =
      (case lookup_constant_fun sym of
        SOME (((_, decl_ty), _), _) =>
          let
            val wanted = ordinary_function_arity sym (length dom);
            val decl_result_ty = drop_fun_type wanted decl_ty;
            val inst_ty = mk_fun_ty (dom, range);
            val inst_result_ty = drop_fun_type wanted inst_ty;
            val declared_shape =
              the_default (default_rust_shape decl_result_ty)
                (function_result_rust_shape seen sym);
            val subst = dictionary_shape_subst const decl_ty inst_ty;
            val instantiated_shape =
              substitute_rust_shape subst declared_shape;
            val extra = Int.max (0, length args - wanted);
            val result_shape =
              drop_shape_arguments extra instantiated_shape;
          in
            if length args < wanted
                orelse shape_type instantiated_shape <> inst_result_ty
            then NONE
            else
              (* Top-level function results already receive the caller's expected
                 polymorphic boundary through argument_expecteds.  Reporting an
                 independently reconstructed Fn source shape here would insert an
                 outer adapter first and discard that call context, e.g. flattening
                 `comp` before its result variable is bound by `word_rec`.  Ordinary
                 result discovery is needed only for a selected function shape
                 hidden below an enclosing type constructor. *)
              (case result_shape of Rust_Tyco _ => SOME result_shape | _ => NONE)
          end
      | NONE => NONE)
    and function_result_rust_shape seen sym =
      if member (op =) seen sym then NONE
      else
        (case lookup_constant_fun sym of
          SOME (((_, ty), raw_eqs), _) =>
            let
              val wanted = ordinary_function_arity sym (arrow_arity ty);
              val result_ty = drop_fun_type wanted ty;
              val eqs = filter (snd o snd) raw_eqs;
              val arg_tys = fst (fun_typs ty);
              fun equation_shape ((pats, body), _) =
                let
                  val vars =
                    (reserved, Symtab.empty)
                    |> rv_intro_typed_pats
                        (ListPair.zip (pats, take (length pats) arg_tys));
                in
                  (case selected_term_rust_shape_seen (sym :: seen) vars body of
                    SOME shape =>
                      if shape_type shape = result_ty then shape
                      else default_rust_shape result_ty
                  | NONE => default_rust_shape result_ty)
                end;
              val shapes = map equation_shape eqs;
              (* A top-level function result already has an explicit eta adapter
                 boundary in print_term_expected and therefore remains the
                 backend's canonical flat Rust Fn in ordinary function signatures.
                 Preserve a selected shape here only when it is nested below a
                 type constructor, where a function adapter cannot convert the
                 enclosing value (for example `Set<nested-Fn>`). *)
              fun signature_shape (shape as Rust_Tyco _) = shape
                | signature_shape _ = default_rust_shape result_ty;
            in
              (case shapes of
                [] => SOME (default_rust_shape result_ty)
              | shape :: rest =>
                  if forall (fn other => other = shape) rest
                  then SOME (signature_shape shape)
                  else SOME (default_rust_shape result_ty))
            end
        | NONE => NONE);
    fun selected_term_rust_shape vars t =
      selected_term_rust_shape_seen [] vars t;
    fun wildcard_unused_pattern used_vars =
      let
        fun wildcard (IVar (SOME v)) =
              if member (op =) used_vars v then IVar (SOME v) else IVar NONE
          | wildcard (t1 `$ t2) = wildcard t1 `$ wildcard t2
          | wildcard ((v, ty) `|=> (t, rty)) = (v, ty) `|=> (wildcard t, rty)
          | wildcard (ICase {term, typ, clauses, primitive}) =
              ICase {
                term = wildcard term,
                typ = typ,
                clauses = map (fn (pat, body) => (wildcard pat, body)) clauses,
                primitive = primitive
              }
          | wildcard t = t
      in wildcard end;
    (** Main term printer. Handles all iterm constructors:
        IConst (constants/constructors), IVar (variables), `$ (application),
        `|=> (lambda/pattern abstraction), ICase (case/let/match).
        The triple (need_box, box_prcs, clone_prcs) controls Box/clone wrapping:
          need_box: whether to wrap the result in Box
          box_prcs: box wrapping function (box_new for exprs, box_pattern for patterns)
          clone_prcs: clone wrapping function (clone for exprs, I for patterns) **)
    fun print_term_gen is_pseudo_fun wrappers some_thm vars fxy t =
          print_term_expected NONE is_pseudo_fun wrappers some_thm vars fxy t
    and print_term_expected expected is_pseudo_fun
        (wrappers as (need_box, box_prcs, _)) some_thm vars fxy t =
          let
            (* A saturated class method whose Self is selected by a recursive
               function dictionary has a non-default result representation even
               when no enclosing constructor or call supplies an expected shape.
               In that position the surrounding function signature, tuple, or
               local expression still uses the backend's ordinary flat type, so
               make that implicit default boundary explicit and adapt back to it.
               A real contextual expectation takes precedence. *)
            val effective_expected =
              (case expected of
                SOME _ => expected
              | NONE =>
                  (case (term_type vars t, selected_term_rust_shape vars t) of
                    (SOME source_ty, SOME (source_shape as Rust_Fn _)) =>
                      let val target_shape = default_rust_shape source_ty in
                        if shape_type source_shape = source_ty
                            andalso source_shape <> target_shape
                        then SOME {hol_type = source_ty,
                          rust_shape = target_shape}
                        else NONE
                      end
                  | _ => NONE));
          in
          (case effective_expected of
            SOME {rust_shape = target_shape as Rust_Fn _, ...} =>
              (case term_type vars t of
                SOME source_ty =>
                  let
                    val source_shape =
                      (case selected_term_rust_shape vars t of
                        SOME shape =>
                          if shape_type shape = source_ty
                          then shape else default_rust_shape source_ty
                      | NONE => default_rust_shape source_ty);
                  in
                  if source_shape <> target_shape
                  then
                    let
                      val adapted = print_function_adapter target_shape
                        is_pseudo_fun some_thm vars t
                    in if need_box then box_prcs adapted else adapted end
                  else print_term_raw effective_expected is_pseudo_fun wrappers some_thm vars fxy t
                  end
              | NONE => print_term_raw effective_expected is_pseudo_fun wrappers some_thm vars fxy t)
          | _ => print_term_raw effective_expected is_pseudo_fun wrappers some_thm vars fxy t)
          end
    and print_term_raw expected is_pseudo_fun (need_box, box_prcs, clone_prcs)
        some_thm vars fxy (IConst const) =
          let
            fun print_const f =
              print_app_with_clone expected is_pseudo_fun
                (box_prcs, clone_prcs) some_thm vars f (const, [])
          in
            print_term_with_cons_and_box (need_box, box_prcs) print_const fxy (IConst const)
          end
      | print_term_raw _ _ _ _ _ _ (IVar NONE) =
          str "_"
      | print_term_raw _ _ (need_box, box_prcs, clone_prcs) _ vars _ (IVar (SOME v)) =
          if need_box
          then box_prcs (clone_prcs (str (rv_lookup_var vars v)))
          else clone_prcs (str (rv_lookup_var vars v))
      | print_term_raw expected is_pseudo_fun (need_box, box_prcs, clone_prcs)
          some_thm vars fxy (t as _ `$ _) =
          let
            fun print_app_term f =
              (case Code_Thingol.unfold_const_app t
              of SOME app => (*function or typeco*)
                print_app_with_clone expected is_pseudo_fun
                  (box_prcs, clone_prcs) some_thm vars f app
              | NONE => (*closure*)
                let
                  val (t', ts') = Code_Thingol.unfold_app t
                  val params = map (print_term_app is_pseudo_fun some_thm vars NOBR) ts'
                  val representation_groups =
                    (case t' of
                      IVar (SOME v) => Option.map rust_shape_groups
                        (rv_lookup_shape vars v)
                    | _ => NONE);
                  val (partial, over_arity) =
                    (case term_type vars t' of
                      SOME callee_ty =>
                        let
                          val (arg_tys, ret_ty) = fun_typs callee_ty
                          val explicit_arity =
                            (case Code_Thingol.unfold_pat_abs t' of
                              ([], _) => length arg_tys
                            | (binds, _) => length binds)
                          val given = length ts'
                        in
                          if given < explicit_arity
                          then
                            let
                              val rem_tys = drop given arg_tys
                              val names =
                                Name.invent (rv_names vars |> snd) "a" (length rem_tys)
                                |> map SOME
                              val rem_vars = map IVar names
                              val full_app = Library.foldl (op `$) (t', ts' @ rem_vars)
                              val lambda_t =
                                (ListPair.zip (names, rem_tys)) `|==> (full_app, ret_ty)
                            in (SOME lambda_t, NONE) end
                          else if given > explicit_arity andalso explicit_arity > 0
                          then (NONE, SOME explicit_arity)
                          else (NONE, NONE)
                        end
                    | NONE => (NONE, NONE))
                in
                  case partial of
                    SOME lambda_t => print_lambda is_pseudo_fun some_thm vars lambda_t
                  | NONE =>
                      let
                        fun print_callee t =
                          (case t of
                            _ `|=> _ =>
                              (* A lambda used immediately as the callee of a
                                 function-value application is already being
                                 split by the surrounding call printer.  Print
                                 only its syntactic binders here; adding
                                 type-level eta binders would consume arguments
                                 that this application boundary is meant to
                                 pass explicitly. *)
                              print_lambda_gen false is_pseudo_fun some_thm vars t
                          | IVar (SOME v) =>
                              (* The surrounding application already consumes
                                 the variable according to its recorded Rust
                                 groups.  Printing it through the standalone-term
                                 path would first normalize a non-default shape
                                 back to flat, recursively constructing the same
                                 adapter while trying to print its own callee. *)
                              str (rv_lookup_var vars v)
                          | _ => print_term_decl is_pseudo_fun some_thm vars NOBR t)
                        fun call callee args =
                          rust_open(
                            str "(*"
                            :: callee
                            :: str ")("
                            :: commas_append args
                            @ [str ")"])
                        fun call_groups callee [] args =
                              if null args then callee else call callee args
                          | call_groups callee (n :: ns) args =
                              let
                                val split_at = Int.min (n, length args);
                                val (args1, args2) = chop split_at args;
                                val next = call callee args1;
                              in
                                if null args2 then next
                                else call_groups next ns args2
                              end;
                      in
                        (case representation_groups of
                          SOME groups => call_groups (print_callee t') groups params
                        | NONE =>
                            (case over_arity of
                              SOME n =>
                                let
                                  val (params1, params2) = chop n params
                                  val first = call (print_callee t') params1
                                in call first params2 end
                            | NONE =>
                                (* The callee is a function value of type
                                   Rc<dyn Fn(..)>, which is not directly callable
                                   (unlike Box, Rc has no Fn impl). Dereference
                                   the Rc before applying the arguments. *)
                                call (print_callee t') params))
                      end
                end)
          in
            print_term_with_cons_and_box (need_box, box_prcs) print_app_term fxy t
          end
      | print_term_raw _ is_pseudo_fun (need_box, box_prcs, _)
          some_thm vars fxy (t as _ `|=> _) =
          (* A lambda is the term-level representation of a HOL function value.
             When such a value inhabits a recursive datatype field, the same
             constructor-field Box decision used for constants and applications
             must also wrap the Rc<dyn Fn(..)> closure. *)
          let
            fun print_abs _ = print_lambda is_pseudo_fun some_thm vars t
          in print_term_with_cons_and_box (need_box, box_prcs) print_abs fxy t end
      | print_term_raw expected is_pseudo_fun (need_box, box_prcs, clone_prcs)
          some_thm vars fxy (ICase case_expr) =
          case Code_Thingol.unfold_const_app (#primitive case_expr)
              of SOME (app as ({ sym = Constant const, ... }, _)) =>
                  if is_none (const_syntax const)
                  then print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy case_expr
                  else
                    let
                      fun print_syntax f =
                        print_app_with_clone expected is_pseudo_fun
                          (box_prcs, clone_prcs) some_thm vars f app
                    in
                      (* A case expression whose primitive has registered syntax
                         (in particular HOL.If) can itself occupy a recursively
                         boxed constructor field.  The syntax printer handles the
                         branches, but the field's Box belongs around the complete
                         conditional expression, just as it does around an ordinary
                         application or lambda in the same constructor position. *)
                      print_term_with_cons_and_box
                        (need_box, box_prcs) print_syntax fxy (ICase case_expr)
                    end
              | NONE => print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy case_expr
    (** Print a term without Box or clone wrapping (for declarations/signatures). **)
    and print_term_decl is_pseudo_fun some_thm vars fxy t =
      print_term_gen is_pseudo_fun (false, I, I) some_thm vars fxy t
    (** Print a term as a pattern (uses box_pattern for Box, no clone). **)
    and print_term_pattern is_pseudo_fun some_thm vars fxy t = 
      print_term_gen is_pseudo_fun (false, box_pattern, I) some_thm vars fxy t
    (** Print a term as an expression (uses box_new and clone). **)
    and print_term_app is_pseudo_fun some_thm vars fxy t = 
      print_term_gen is_pseudo_fun (false, box_new, clone) some_thm vars fxy t
    (** Prepend type constructor prefix (e.g. "List::") and apply Box wrapping if needed. **)
    and print_term_with_cons_and_box (need_box, box_prcs) print_term fxy t =
      let
        fun lookup_typeco t =
          (case (Code_Thingol.unfold_const_app t)
            of (SOME ((const as {sym as (Constant c), ...}), _))
              => lookup_constant_typeco sym
            | _ => NONE)
        (* The `Enum::` prefix is the (possibly crate-qualified) name of the parent
           datatype, taken straight from the deresolver so it matches the enum
           declaration and resolves across modules without a glob import. *)
        fun print_cons (SOME parent) = tyco_name_str parent
          | print_cons NONE = ""
        (* An UNDER-applied constructor -- given fewer arguments than its domain,
           including the zero-argument case -- is eta-expanded into a closure by
           print_app_expr (saturated_application), so it must NOT get the `Tyco::`
           prefix: that belongs only on a fully-applied constructor reference.
           A partial application such as `Cons x` (1 of 2 args) would otherwise
           print as the invalid `List::{ ..closure.. }`. *)
        val is_eta_constr =
          (case Code_Thingol.unfold_const_app t
            of SOME (({ dom, ... }), ts) => length ts < length dom
            | _ => false)
        (* When a constructor has registered const_syntax (e.g. Product_Type.Pair
           mapped to native tuple syntax "!(_, _)"), the template already encodes
           the full printed form.  Prepending Tyco:: would produce malformed output
           like "Prod::(a, b)".  Suppress the prefix whenever custom syntax is in use. *)
        val has_const_syntax =
          (case Code_Thingol.unfold_const_app t
            of SOME ({sym = Constant c, ...}, _) => is_some (const_syntax c)
            | _ => false)
        val typeco_s =
          if is_eta_constr orelse has_const_syntax then ""
          else print_cons (lookup_typeco t)
        (* When a `Tyco::` prefix is prepended, the constructor application is
           atomic (`Tyco::Cons(args)` never needs outer brackets), so print it at
           NOBR -- otherwise gen_print_app may brackify it at BR and the prefix
           lands outside the parens, producing the invalid `Tyco::(Cons(args))`.
           Non-prefixed terms keep fxy so infix operands still bracket correctly. *)
        val term = print_term (if typeco_s = "" then fxy else NOBR)
        val term_with_cons =
          if typeco_s = "" then term
          else rust_open [str (typeco_s ^ "::"), term]
        val term_with_box =
          if need_box
          then (box_prcs term_with_cons)
          else term_with_cons
      in
        term_with_box
      end
    (** Print a function/constructor application expression.
        Handles constructors (with Box wrapping per argument),
        pseudo-functions, and regular functions (with generic prefix for trait dispatch). **)
    and print_app_expr expected is_pseudo_fun (box_prcs, clone_prcs)
       some_thm vars (app as ((const as { sym, dicts, dom, range, ... }), ts)) =
        if is_constr sym then
          let
            val wanted = length dom
            val need_box_list = box_table sym
            val expected_args = argument_expecteds expected sym dom range
            (* One PhantomData marker per phantom param of the parent datatype,
               appended after the real args.  Recover each marker's concrete
               type from this constructor occurrence's instantiated result.  A
               phantom constructor has no ordinary field from which Rust can
               infer that type: when it is passed to another generic function,
               a bare `PhantomData` otherwise introduces an unrelated inference
               variable and triggers E0283 even though HOL fixed the type.  The
               explicit `PhantomData::<T>` path remains valid as both an
               expression and an irrefutable pattern. *)
            val phantom_vs =
              (case lookup_constant_typeco sym of
                SOME parent => phantom_table (Type_Constructor parent)
              | NONE => [])
            val phantom_types =
              (case (lookup_constructor_fields sym, range) of
                (SOME (parent, vs, _), range_parent `%% range_args) =>
                  if parent = range_parent andalso length vs = length range_args
                  then
                    let
                      val subst = ListPair.zip (vs, range_args)
                    in map (fn v => AList.lookup (op =) subst v) phantom_vs end
                  else replicate (length phantom_vs) NONE
              | _ => replicate (length phantom_vs) NONE)
            fun print_phantom_arg (SOME ty) =
                  Pretty.block [str "PhantomData::<", print_typ NOBR ty, str ">"]
              | print_phantom_arg NONE = str "PhantomData"
            val phantom_args = map print_phantom_arg phantom_types
            val phantom_count = length phantom_args
          in
            if wanted = 0
            then
              if phantom_count = 0
              then [(str o deresolve_base) sym]
              else [Pretty.block [(str o deresolve_base) sym, str " ", rust_parens phantom_args]]
            else if length ts = wanted
            then
              [rust_open [
                (str o deresolve_base) sym,
                str " ",
                rust_parens
                  (map2
                    (fn (t, need_box) => fn expected_arg =>
                      print_term_expected expected_arg is_pseudo_fun
                        (need_box, box_prcs, clone_prcs) some_thm vars NOBR t)
                    (ListPair.zip (ts, need_box_list)) expected_args
                   @ phantom_args)]]
            else 
              let 
                val saturated_t = Code_Thingol.saturated_application wanted app
              in
                [print_term_expected expected is_pseudo_fun
                  (false, box_prcs, clone_prcs) some_thm vars NOBR saturated_t]
              end
          end
        else if is_pseudo_fun sym
          then (str o deresolve) sym @@ str "()"
        else
          let 
            val method_arity = trait_method_arity sym
            val is_trait_method_call = is_some method_arity
            val wanted_app =
              if is_trait_method_call
              then
                (* Trait method signatures are governed by the class parameter's
                   declared arity. This is deliberately independent of the
                   implementing constant's instantiated Rust type: for an instance
                   at HOL `fun`, the method result/arguments may themselves be
                   function values and must remain a single `Self` parameter or
                   result in Rust, not leak extra closure arguments into the method
                   call. *)
                the method_arity
              else length dom
            val expected_args =
              if is_trait_method_call
              then trait_argument_expecteds const
              else dictionary_argument_expecteds expected const
            (** Mirror the eta-expansion in binding_of_stmt: a single equation with
                empty LHS (e.g., [size_list = gen_length zero_nat]) is eta-expanded
                to one argument before being emitted as a Rust function. **)
            val wanted_fn =
              if is_trait_method_call
              then
                (* Class parameters and reconstructed concrete instance methods
                   are emitted through Rust trait methods (`A::method` or
                   `Tyco::method`) whose signatures consume every top-level HOL
                   arrow as one uncurried Rust parameter.  A concrete instance
                   equation may be eta-reduced (for example one pattern returning
                   a closure for a two-arrow method), but print_inst_impl
                   eta-expands the impl body to the trait arity.  Calls printed as
                   trait methods must therefore use the instantiated method arity,
                   not the raw equation's LHS length, so `m x y` prints as
                   `T::m(x, y)` rather than as a call of a returned
                   `Rc<dyn Fn(..)>`. *)
                wanted_app
              else ordinary_function_arity sym wanted_app
            (** After the Rust function's equation parameters are consumed, the
                remaining HOL arrows describe calls on its returned function
                value.  Preserve a polymorphic result boundary here as well: for
                `comp`, a result variable instantiated by `A => A` changes the
                residual shape from `[Nat, A]` to `[Nat][A]`, so the two arguments
                must be emitted as successive Rc<dyn Fn> calls. **)
            val ordinary_returned_groups =
              (case lookup_constant_fun sym of
                SOME (((_, decl_ty), _), _) =>
                  let
                    fun drop_fun 0 ty = ty
                      | drop_fun n ("fun" `%% [_, rty]) = drop_fun (n - 1) rty
                      | drop_fun _ ty = ty;
                    val decl_tail = drop_fun wanted_fn decl_ty;
                    val inst_tail = mk_fun_ty (drop wanted_fn dom, range);
                    val subst = add_default_shape_subst decl_tail inst_tail [];
                  in rust_shape_groups
                    (instantiate_rust_shape subst decl_tail inst_tail) end
              | NONE => [])
            val prefix_target_shape = trait_receiver_shape const
            val returned_groups =
              if is_trait_method_call
              then
                (case trait_result_shape const of
                  SOME shape => rust_shape_groups shape
                | NONE => [])
              else ordinary_returned_groups
            (* For a class-method (classparam) call, the type to dispatch on is the
               class's own type variable, carried by the dictionary — NOT
               necessarily the first argument's type. For `equal :: 'a => ..` they
               coincide, but for `len_of :: 'a itself => nat` the argument is
               `'a itself` while dispatch is on the phantom `'a`. The leading
               Dict_Var names that type variable, giving `A::method(..)`. *)
            val classparam_dispatch_var =
              let
                fun plain_var (Code_Thingol.Dict_Var {var, ...}) = SOME var
                  | plain_var (Code_Thingol.Dict_Const _) = NONE
                fun dict_var (Code_Thingol.Dict (_, plain)) = plain_var plain
              in get_first dict_var (List.concat dicts) end
            (* Return-type polymorphism turbofish. When a generic parameter of the
               called function occurs ONLY in its result type and not in any
               argument type, the call site has nothing from which to infer that
               type argument, so rustc reports E0282 ("type annotations needed").
               Emit an explicit `name::<T..>(..)` reconstructed from the concrete
               types this IConst is instantiated to. Only plain (non-constructor,
               non-method, non-pseudo) `fun` definitions are affected; class
               methods dispatch through a `Receiver::` prefix instead. The type
               arguments are aligned to the declared generic order — the same
               traversal the fn declaration uses to print its `<..>` list — and
               each is filled from a substitution matching the declared
               polymorphic signature against the instantiated dom/range. *)
            val turbofish =
              if is_some (lookup_method_class sym) orelse is_some (inst_method_info sym)
              then NONE
              else
                (case lookup_constant_fun sym of
                    NONE => NONE
                  | SOME (((_, decl_ty), _), _) =>
                      let
                        fun tyvars_in t =
                          let
                            fun aux (ITyVar v, acc) = insert (op =) v acc
                              | aux ((_ `%% ts), acc) = List.foldl aux acc ts
                          in aux (t, []) end
                        val (decl_doms_all, decl_final) = Code_Thingol.unfold_fun decl_ty
                        val n = length dom
                        val decl_arg_tys = take n decl_doms_all
                        val decl_res_tys = drop n decl_doms_all @ [decl_final]
                        val tyvars_of_list =
                          List.foldl (fn (t, acc) => union (op =) (tyvars_in t) acc) []
                        val arg_tyvars = tyvars_of_list decl_arg_tys
                        val res_tyvars = tyvars_of_list decl_res_tys
                        val return_only = subtract (op =) arg_tyvars res_tyvars
                        (* Declared generic parameters, in the order the fn decl
                           prints them (see print_generics_and_traits). *)
                        fun decl_generics t =
                          let
                            fun aux (ITyVar v, acc) = v :: acc
                              | aux ((_ `%% ts), acc) = List.foldl aux acc ts
                          in distinct (op =) (aux (t, [])) end
                        val gens = decl_generics decl_ty
                        (* declared tyvar -> instantiated itype, by structural
                           match of the declared full type vs. the instantiated one. *)
                        fun mk_fun ([], r) = r
                          | mk_fun (d :: ds, r) = "fun" `%% [d, mk_fun (ds, r)]
                        val inst_ty = mk_fun (dom, range)
                        fun unify (ITyVar v, inst) subst =
                              if AList.defined (op =) subst v then subst
                              else (v, inst) :: subst
                          | unify (_ `%% ds, _ `%% is) subst =
                              if length ds = length is
                              then List.foldl (fn ((d, i), s) => unify (d, i) s)
                                     subst (ListPair.zip (ds, is))
                              else subst
                          | unify (_, _) subst = subst
                        val subst = unify (decl_ty, inst_ty) []
                      in
                        if null return_only orelse null gens then NONE
                        else SOME (enum "," "::<" ">"
                          (map (fn v =>
                             case AList.lookup (op =) subst v of
                               SOME ity => print_typ NOBR ity
                             | NONE => str "_") gens))
                      end)
            (* Rust permits several traits in scope to expose the same associated
               function name (notably binary lattice `sup` and complete-lattice
               `sup`).  A bare `Receiver::method` is then ambiguous, and for a
               concrete receiver its trait may not be imported at all.  Whenever
               the class parameter identifies its declaring class, render the
               call as `<Receiver as Trait>::method`; this also handles mapped and
               mixfix receiver types without requiring a nominal path. *)
            fun qualified_trait_prefix recv_shape class =
              Pretty.block
                [str "<", print_rust_shape recv_shape, str " as ",
                 str (deresolve_class class), str ">::"];
            (* Decide the printed callee and any fully-qualified trait prefix. *)
            val (generic_prefixs, funcname) =
              (case inst_method_info sym of
                  SOME (tyco_s, cp_s) =>
                    (case lookup_method_class (Constant cp_s) of
                        SOME class =>
                          ([qualified_trait_prefix prefix_target_shape class],
                           str (deresolve_base (Constant cp_s)))
                      | NONE =>
                          ([Pretty.block [str (tyco_name_str tyco_s), str "::"]],
                           str (deresolve_base (Constant cp_s))))
                | NONE =>
                    (case lookup_method_class sym of
                      SOME class =>
                        let
                          val recv_shape =
                            (case classparam_dispatch_var of
                              SOME v => Rust_Var v
                            | NONE => prefix_target_shape)
                        in
                          ([qualified_trait_prefix recv_shape class],
                           (str o deresolve_base) sym)
                        end
                    | NONE => ([], (str o deresolve) sym)))
          in
            if (if is_trait_method_call then length ts >= wanted_app else length ts = wanted_app)
            then
              let
                val (ts1, ts2) = chop wanted_fn ts
                val (expected1, expected2) = chop wanted_fn expected_args
                fun print_args expecteds args =
                  map2 (fn expected_arg => fn t =>
                    print_term_expected expected_arg is_pseudo_fun
                      (false, box_prcs, clone_prcs) some_thm vars NOBR t)
                    expecteds args
                fun call_rc callee args =
                  Pretty.block [str "(*", callee, str ")", rust_parens args]
                val call1 =
                  generic_prefixs
                  @ funcname
                  :: the_list turbofish
                   @ [rust_parens
                       (print_args expected1 ts1)]
              in
                if List.null ts2
                then [Pretty.block call1]
                else
                  let
                    fun call_groups callee [] args expecteds =
                          call_rc callee (print_args expecteds args)
                      | call_groups callee (n :: ns) args expecteds =
                          let
                            val split_at = Int.min (n, length args);
                            val (args1, args2) = chop split_at args;
                            val (expected1, expected2) = chop split_at expecteds;
                            val next = call_rc callee
                              (print_args expected1 args1);
                          in
                            if null args2 then next
                            else call_groups next ns args2 expected2
                          end;
                    val result = call_groups (Pretty.block call1)
                      returned_groups ts2 expected2;
                  in [result] end
              end
            else
              let 
                val saturated_t = Code_Thingol.saturated_application wanted_app app
              in
                [print_term_expected expected is_pseudo_fun
                  (false, box_prcs, clone_prcs) some_thm vars NOBR saturated_t]
              end
          end
    (** Print an application, applying registered const_syntax if any and
        otherwise falling back to print_app_expr. print_app prints arguments
        without Box/clone; print_app_with_clone threads the (box_prcs, clone_prcs)
        wrappers through both ordinary calls and custom-syntax subterms. **)
    and gen_print_app_rvars expected print_app_expr print_term some_thm vars fxy
        (app as (const as { sym, dom, range, ... }, ts)) =
      (case sym of
        Constant name =>
          let
            val expected_args = argument_expecteds expected sym dom range
            fun print_args fxy expecteds args =
              map2 (fn expected_arg => fn t =>
                print_term expected_arg some_thm vars fxy t) expecteds args;
            fun print_registered_syntax () =
              (case const_syntax name of
                NONE => brackify fxy (print_app_expr some_thm vars app)
              | SOME (_, Plain_printer s) =>
                  brackify fxy (str s :: print_args BR expected_args ts)
              | SOME (wanted, Complex_printer print) =>
                  let
                    val ((vs_tys, (ts1, rty)), ts2) =
                      Code_Thingol.satisfied_application wanted app;
                    val (expected1, expected2) = chop wanted expected_args;
                    fun expected_of t =
                      let val i = find_index (fn t' => t' = t) ts1
                      in if i < 0 then NONE else List.nth (expected1, i) end;
                    fun print_term_raw some_thm raw_vars fxy t =
                      print_term (expected_of t) some_thm
                        (raw_vars, rv_types vars) fxy t;
                    fun print' fxy =
                      print (print_term_raw some_thm) some_thm (rv_names vars) fxy (ts1 ~~ take wanted dom);
                  in
                    if null vs_tys then
                      if null ts2 then
                        print' fxy
                      else
                        brackify fxy (print' APP :: print_args BR expected2 ts2)
                    else
                      print_term expected some_thm vars fxy
                        (vs_tys `|==> (IConst const `$$ ts1, rty))
                  end)
          in
            (case (name, ts) of
              ("Product_Type.Pair", [left, right]) =>
                rust_parens
                  (print_args NOBR expected_args [left, right])
            | ("HOL.If", [cond, then_t, else_t]) =>
                rust_if
                  (print_term NONE some_thm vars NOBR cond)
                  (print_term expected some_thm vars NOBR then_t)
                  (print_term expected some_thm vars NOBR else_t)
            | _ => print_registered_syntax ())
          end
      | _ => brackify fxy (print_app_expr some_thm vars app))
    and print_app is_pseudo_fun some_thm vars =
      gen_print_app_rvars NONE (print_app_expr NONE is_pseudo_fun (I, I))
      (fn expected => print_term_expected expected is_pseudo_fun (false, I, I))
      some_thm vars
    and print_app_with_clone expected is_pseudo_fun (box_prcs, clone_prcs) some_thm vars =
      gen_print_app_rvars expected
      (print_app_expr expected is_pseudo_fun (box_prcs, clone_prcs))
      (fn expected => print_term_expected expected is_pseudo_fun
        (false, box_prcs, clone_prcs)) some_thm vars
    (** Bind a clause pattern, introducing its variables (printed as a pattern). **)
    and print_bind_typed is_pseudo_fun some_thm fxy pat ty vars =
      let val vars' = rv_intro_typed_pat pat ty vars
      in (print_term_pattern is_pseudo_fun some_thm vars' fxy pat, vars') end
    and print_bind_typed_shape is_pseudo_fun some_thm fxy pat ty shape vars =
      let
        val vars' = rv_intro_typed_pat_shape pat ty shape vars;
        val printed_pat =
          (case pat of
            IVar (SOME v) => str (rv_lookup_var vars' v)
          | _ => print_term_pattern is_pseudo_fun some_thm vars' fxy pat);
      in (printed_pat, vars') end
    and pat_contains_boxed_field pat =
      (case Code_Thingol.unfold_const_app pat of
        SOME ({sym, ...}, ts) =>
          if is_constr sym then
            let
              val boxes = box_table sym;
              val boxed_here =
                length boxes = length ts andalso
                  exists (fn (_, need_box) => need_box) (ListPair.zip (ts, boxes));
            in boxed_here orelse exists pat_contains_boxed_field ts end
          else exists pat_contains_boxed_field ts
      | NONE => false)
    and pat_irrefutable pat =
      (case pat of
        IVar _ => true
      | _ =>
          (case Code_Thingol.unfold_const_app pat of
            SOME ({sym, ...}, ts) =>
              is_single_constr sym andalso List.all pat_irrefutable ts
          | NONE => false))
    and print_irrefutable_case_parts is_pseudo_fun (need_box, box_prcs, clone_prcs)
        some_thm vars (case_expr as {clauses = [_], ...}) =
          let
            val (binds, body) = Code_Thingol.unfold_let (ICase case_expr);
            fun print_let ((pat, ty), t) vars =
              vars
              |> print_bind_typed is_pseudo_fun some_thm NOBR pat ty
              |>> (fn p => rust_open
                  [str "let ", p, str " = ",
                  print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars NOBR t, str ";"])
            val (ps, vars') = fold_map print_let binds vars;
            val all_irrefutable = List.all (pat_irrefutable o fst o fst) binds;
          in
            if all_irrefutable andalso not (exists (pat_contains_boxed_field o fst) (map fst binds))
            then SOME (ps, print_term_app is_pseudo_fun some_thm vars' NOBR body)
            else NONE
          end
      | print_irrefutable_case_parts _ _ _ _ _ = NONE
    and stable_match_compile is_pseudo_fun some_thm vars columns rows fallback =
      let
        fun emit_row (_, _, _, lets, body) =
          if null lets then body else rust_bare_block (lets @ [body]);
        fun first_pat (p :: _) = SOME p
          | first_pat [] = NONE;
        fun is_irrefutable_col_pat (IVar _) = true
          | is_irrefutable_col_pat _ = false;
        fun source_var_of_scrutinee row_vars scrutinee =
          let
            val scrutinee_s = Pretty.unformatted_string_of scrutinee;
            val (namemap, _) = rv_names row_vars;
          in
            get_first (fn (v, printed) =>
              if printed = scrutinee_s then SOME v else NONE) (Symtab.dest namemap)
          end;
        fun binding_let row_vars used_vars scrutinee (IVar (SOME v)) =
              if member (op =) used_vars v
              then
                let
                  val lhs = rv_lookup_var row_vars v
                  val scrutinee_s = Pretty.unformatted_string_of scrutinee
                  val rhs =
                    (* An irrefutable variable pattern can introduce an alias of an
                       already-bound owned value. If the source variable is also used
                       later in the selected row, the alias must be initialized from a
                       clone; otherwise the alias binding would move the source before
                       the later use. *)
                    (case source_var_of_scrutinee row_vars scrutinee of
                      SOME src_v =>
                        if lhs <> scrutinee_s
                          andalso src_v <> v
                          andalso member (op =) used_vars src_v
                        then clone scrutinee
                        else scrutinee
                    | NONE => scrutinee);
                in
                  if lhs = Pretty.unformatted_string_of scrutinee
                  then []
                  else [rust_open [str "let ", str lhs, str " = ", rhs, str ";"]]
                end
              else []
          | binding_let _ _ _ _ = [];
        fun row_pats (pats, _, _, _, _) = pats;
        (* Product_Type.Pair is printed with native Rust tuple syntax and therefore
           has no surviving Datatypecons node in the Thingol program.  Treat it as
           a synthetic constructor while compiling stable matches; otherwise a
           boxed pattern below a tuple (for example `(t, (k, v) # xs)`) has no
           constructor column and incorrectly falls through to the non-exhaustive
           fallback. *)
        fun is_native_tuple (Constant "Product_Type.Pair") = true
          | is_native_tuple _ = false;
        fun constructor_pat pat =
          (case Code_Thingol.unfold_const_app pat of
            SOME ({sym, dom, ...}, ts) =>
              if (is_constr sym orelse is_native_tuple sym)
                  andalso length dom = length ts
              then SOME (sym, dom, ts)
              else NONE
          | NONE => NONE);
        fun constructor_name sym =
          (case lookup_constant_typeco sym of
            SOME parent => tyco_name_str parent ^ "::" ^ deresolve_base sym
          | NONE => deresolve_base sym);
        fun constructor_pattern sym field_names =
          let
            val phantom_count =
              (case lookup_constant_typeco sym of
                SOME parent => length (phantom_table (Type_Constructor parent))
              | NONE => 0);
            val phantom_args = List.tabulate (phantom_count, fn _ => str "PhantomData");
            val args = map str field_names @ phantom_args;
          in
            if is_native_tuple sym then rust_parens (map str field_names)
            else if null args then str (constructor_name sym)
            else Pretty.block [str (constructor_name sym), str " ", rust_parens args]
          end;
        fun fresh_names row_vars base n =
          Name.invent (snd (rv_names row_vars)) base n;
        fun compile [] [] rows _ =
              (case rows of [] => fallback | row :: _ => emit_row row)
          | compile columns _ [] _ = fallback
          | compile ((scrutinee, _) :: rest_columns) all_columns rows depth =
              let
                val first_pats = map_filter (first_pat o #1) rows;
                val all_irrefutable =
                  not (null first_pats) andalso List.all is_irrefutable_col_pat first_pats;
                fun drop_irrefutable (pats as p :: ps, row_vars, used_vars, lets, body) =
                      (ps, row_vars, used_vars,
                        lets @ binding_let row_vars used_vars scrutinee p, body)
                  | drop_irrefutable row = row;
              in
                if all_irrefutable then
                  compile rest_columns rest_columns (map drop_irrefutable rows) depth
                else
                  let
                    val constructors =
                      rows
                      |> map_filter (fn row =>
                          (case first_pat (row_pats row) of
                            SOME p => Option.map #1 (constructor_pat p)
                          | NONE => NONE))
                      |> distinct (op =);
                    val base_vars =
                      (case rows of
                        (_, row_vars, _, _, _) :: _ => row_vars
                      | [] => vars);
                    fun exact_rows_for_constructor sym =
                      map_filter (fn (pats as p :: ps, row_vars, used_vars, lets, body) =>
                          (case constructor_pat p of
                            SOME (sym', dom, ts) =>
                              if sym = sym'
                              then SOME (dom, ts, ps, row_vars, used_vars, lets, body)
                              else NONE
                          | NONE => NONE)
                        | _ => NONE) rows;
                    fun irrefutable_binding_used (p, _, used_vars, _, _) =
                      (case p of
                        IVar (SOME v) => member (op =) used_vars v
                      | _ => false);
                    val irrefutable_rows =
                      map_filter (fn (pats as p :: ps, row_vars, used_vars, lets, body) =>
                          if is_irrefutable_col_pat p
                          then SOME (p, row_vars, used_vars, lets, body)
                          else NONE
                        | _ => NONE) rows;
                    val needs_whole_scrutinee =
                      exists irrefutable_binding_used irrefutable_rows;
                    val whole_name =
                      hd (fresh_names base_vars ("whole" ^ Int.toString depth) 1);
                    val whole_scrutinee = str whole_name;
                    val irrefutable_scrutinee =
                      if needs_whole_scrutinee then whole_scrutinee else scrutinee;
                    fun print_constructor_arm sym =
                      let
                        val exact_rows = exact_rows_for_constructor sym;
                        val (dom, ts0, _, row_vars0, _, _, _) = hd exact_rows;
                        val wildcard_fields = replicate (length dom) (IVar NONE);
                        (* Pattern-matrix specialization keeps irrefutable rows
                           in every constructor branch, in their original order.
                           Restricting the branch to exact-constructor rows makes
                           later wildcard equations unreachable. *)
                        val spec_rows =
                          map_filter (fn (pats as p :: ps, row_vars, used_vars, lets, body) =>
                              (case constructor_pat p of
                                SOME (sym', _, ts) =>
                                  if sym = sym'
                                  then SOME (ts, ps, row_vars, used_vars, lets, body)
                                  else NONE
                              | NONE =>
                                  if is_irrefutable_col_pat p
                                  then SOME (wildcard_fields, ps, row_vars, used_vars,
                                    lets @ binding_let row_vars used_vars
                                      irrefutable_scrutinee p, body)
                                  else NONE)
                            | _ => NONE) rows;
                        val boxes0 = box_table sym;
                        val boxes =
                          if length boxes0 = length dom then boxes0 else map (K false) dom;
                        val temp_names = fresh_names row_vars0 ("p" ^ Int.toString depth) (length dom);
                        fun field_entries i =
                          map (fn (ts, _, row_vars, used_vars, _, _) =>
                            (nth ts i, row_vars, used_vars)) spec_rows;
                        fun used_name (IVar (SOME v), row_vars, used_vars) =
                              if member (op =) used_vars v
                              then SOME (rv_lookup_var row_vars v)
                              else NONE
                          | used_name _ = NONE;
                        fun bound_name (IVar (SOME v), row_vars, _) =
                              SOME (rv_lookup_var row_vars v)
                          | bound_name _ = NONE;
                        fun direct_field_name used_direct i need_box =
                          let
                            val entries = field_entries i;
                            val used_names = distinct (op =) (map_filter used_name entries);
                            val bound_names = map_filter bound_name entries;
                            val all_vars =
                              List.all (fn (pat, _, _) => is_irrefutable_col_pat pat) entries;
                          in
                            if not all_vars then NONE
                            else
                              (case used_names of
                                [] => SOME "_"
                              | [name] =>
                                  if need_box
                                    orelse member (op =) used_direct name
                                    orelse not (List.all (fn name' => name' = name) bound_names)
                                  then NONE
                                  else SOME name
                              | _ => NONE)
                          end;
                        fun field_decision (i, (ty, need_box, temp)) (decisions, used_direct) =
                          (case direct_field_name used_direct i need_box of
                            SOME name =>
                              ((name, NONE) :: decisions,
                                if name = "_" then used_direct else name :: used_direct)
                          | NONE =>
                              let
                                val scrutinee =
                                  if need_box
                                  then Pretty.block [str "*", str temp]
                                  else str temp;
                              in
                                ((temp, SOME (scrutinee, ty)) :: decisions, used_direct)
                              end);
                        val (field_decisions, _) =
                          fold field_decision
                            (map_index (fn (i, (ty, (need_box, temp))) =>
                              (i, (ty, need_box, temp)))
                              (ListPair.zip (dom, ListPair.zip (boxes, temp_names))))
                            ([], []);
                        val field_decisions = rev field_decisions;
                        val field_names = map #1 field_decisions;
                        val field_columns = map_filter #2 field_decisions;
                        fun kept_field_pats ts =
                          map_filter (fn (pat, (_, col)) =>
                            (case col of SOME _ => SOME pat | NONE => NONE))
                            (ListPair.zip (ts, field_decisions));
                        val specialized_rows =
                          map (fn (ts, ps, row_vars, used_vars, lets, body) =>
                            (kept_field_pats ts @ ps, row_vars, used_vars, lets, body)) spec_rows;
                        val arm_body =
                          compile (field_columns @ rest_columns)
                            (field_columns @ rest_columns) specialized_rows (depth + 1);
                      in
                        rust_arm (constructor_pattern sym field_names) arm_body
                      end;
                    val default_rows =
                      map_filter (fn (pats as p :: ps, row_vars, used_vars, lets, body) =>
                          if is_irrefutable_col_pat p
                          then SOME (ps, row_vars, used_vars,
                            lets @ binding_let row_vars used_vars
                              irrefutable_scrutinee p, body)
                          else NONE
                        | _ => NONE) rows;
                    val default_arm =
                      if null default_rows then []
                      else
                        [rust_arm (str "_")
                          (compile rest_columns rest_columns default_rows (depth + 1))];
                    val fallback_arm =
                      if null default_rows
                      then [rust_arm (str "_") fallback]
                      else default_arm;
                  in
                    if null constructors then fallback
                    else
                      let
                        val match_expr =
                          rust_match scrutinee
                            (map print_constructor_arm constructors @ fallback_arm);
                      in
                        if needs_whole_scrutinee
                        then rust_bare_block
                          [rust_open [str "let ", whole_scrutinee, str " = ",
                            clone scrutinee, str ";"], match_expr]
                        else match_expr
                      end
                  end
              end;
      in
        compile columns columns rows 0
      end
    (** Print a case expression. Three cases:
        - Empty clauses: generates panic
        - Single irrefutable clause: emitted as a let-binding expression block
        - Multiple clauses: emitted as match block **)
    and print_case _ _ _ _ _ { clauses = [], ... } =
          (concat o map str) ["panic!(\"empty case\")", "\"empty case\""]
      | print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy (case_expr as { clauses = [_], ... }) =
          let
            fun print_stable_match t ty clauses =
              let
                fun row (pat, body) =
                  let
                    val vars' = rv_intro_typed_pat pat ty vars;
                    val used_vars = build (Code_Thingol.add_varnames body);
                  in
                    ([pat], vars', used_vars, [],
                      print_term_app is_pseudo_fun some_thm vars' NOBR body)
                  end;
                val scrutinee = print_term_app is_pseudo_fun some_thm vars NOBR t;
              in
                stable_match_compile is_pseudo_fun some_thm vars
                  [(scrutinee, ty)] (map row clauses)
                  (str "panic!(\"non-exhaustive match\")")
              end;
          in
            (case print_irrefutable_case_parts is_pseudo_fun
                (need_box, box_prcs, clone_prcs) some_thm vars case_expr of
              SOME (ps, body) => rust_bare_block (ps @ [body])
            | NONE =>
              (case case_expr of {term = t, typ = ty, clauses = clauses, ...} =>
                let
                  val has_boxed_patterns = exists (pat_contains_boxed_field o fst) clauses;
                  fun print_select (pat, body) =
                    let
                      val used_vars = build (Code_Thingol.add_varnames body);
                      val pat' = wildcard_unused_pattern used_vars pat;
                      val vars' = rv_intro_typed_pat pat ty vars;
                      val p = print_term_pattern is_pseudo_fun some_thm vars' NOBR pat';
                    in
                      rust_arm p (print_term_app is_pseudo_fun some_thm vars' NOBR body)
                    end
                in
                  if has_boxed_patterns
                  then print_stable_match t ty clauses
                  else
                    rust_match
                      (print_term_app is_pseudo_fun some_thm vars NOBR t)
                      (map print_select clauses
                        @ [rust_arm (str "_") (str "panic!(\"non-exhaustive match\")")])
                end))
          end
        (*match block*)
      | print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars _ (icase as { term = t, typ = _, clauses = clauses, ... }) =
          let
            val has_boxed_patterns = exists (pat_contains_boxed_field o fst) clauses;
            fun print_stable_match () =
              let
                val ty = #typ icase;
                fun row (pat, body) =
                  let
                    val vars' = rv_intro_typed_pat pat ty vars;
                    val used_vars = build (Code_Thingol.add_varnames body);
                  in
                    ([pat], vars', used_vars, [],
                      print_term_app is_pseudo_fun some_thm vars' NOBR body)
                  end;
                val scrutinee = print_term_app is_pseudo_fun some_thm vars NOBR t;
              in
                stable_match_compile is_pseudo_fun some_thm vars
                  [(scrutinee, ty)] (map row clauses)
                  (str "panic!(\"non-exhaustive match\")")
              end;
            fun print_select (pat, body) =
              let
                val used_vars = build (Code_Thingol.add_varnames body);
                val pat' = wildcard_unused_pattern used_vars pat;
                val vars' = rv_intro_typed_pat pat (#typ icase) vars;
                val p = print_term_pattern is_pseudo_fun some_thm vars' NOBR pat';
              in
                rust_arm p (print_term_app is_pseudo_fun some_thm vars' NOBR body)
              end;
          in
            (* HOL functions may be partial (e.g. `nth [] n` has no equation), so
               the clauses need not cover every constructor; Rust requires total
               matches. Add a catch-all that panics on the undefined inputs. On a
               match that is already exhaustive this arm is unreachable — a warning
               (suppressed), not an error. *)
            if has_boxed_patterns
            then print_stable_match ()
            else
              rust_match
                (print_term_app is_pseudo_fun some_thm vars NOBR t)
                (map print_select clauses
                  @ [rust_arm (str "_") (str "panic!(\"non-exhaustive match\")")])
          end
    (** Adapt the backend's default flat function value to a contextual parameter
        grouping.  One invocation builds the outer group and an ordinary flat
        lambda for all remaining arguments.  That inner lambda is printed with
        the target result shape, so print_term_expected recursively inserts the
        next adapter when the target contains further groups.  Reusing the normal
        lambda printer at every level preserves its capture cloning, return-type
        annotation and Rc unsizing rules. **)
    and print_function_adapter (target_shape as Rust_Fn (outer_shapes, inner_shape))
        is_pseudo_fun some_thm vars t =
      let
        val target_ty = shape_type target_shape;
        val (inst_args, inst_ret) = fun_typs target_ty;
        val outer_arity = length outer_shapes;
        val names =
          Name.invent (rv_names vars |> snd) "boundary_arg" (length inst_args)
          |> map SOME;
        val args = map IVar names;
        val (outer_names, inner_names) = chop outer_arity names;
        val (outer_tys, inner_tys) = chop outer_arity inst_args;
        val full_app = Library.foldl (op `$) (t, args);
        val inner_ty = shape_type inner_shape;
        val inner_lambda =
          (ListPair.zip (inner_names, inner_tys)) `|==> (full_app, inst_ret);
        val outer_lambda =
          (ListPair.zip (outer_names, outer_tys)) `|==> (inner_lambda, inner_ty);
        val inner_expected =
          SOME {hol_type = inner_ty, rust_shape = inner_shape};
        val closure =
          print_lambda_gen_limit_expected inner_expected (SOME outer_shapes)
            false (SOME outer_arity)
            is_pseudo_fun some_thm vars outer_lambda;
      in
        rust_open [str "((", closure, str ") as ",
          print_rust_shape target_shape, str ")"]
      end
      | print_function_adapter _ _ _ _ _ =
          error "Rust function adapter requires a function target shape"
    (** Print a `move` closure with explicit capture-by-clone.
        For each outer variable v that occurs free in the body 
        we emit `let v_cap = v.clone();` before the closure
        and rewrite the in-body occurrences to v_cap.
        Closure parameter names (collected via add_varnames on each bind
        pattern) are excluded from the capture set. **)
    and print_lambda_parts_gen eta_tail is_pseudo_fun some_thm vars t =
      print_lambda_parts_limit NONE NONE eta_tail NONE
        is_pseudo_fun some_thm vars t
    and print_lambda_parts_limit body_expected bind_shapes eta_tail bind_limit
        is_pseudo_fun some_thm vars t =
      let
        val (binds0, body0) =
          (case bind_limit of
            NONE => Code_Thingol.unfold_pat_abs t
          | SOME limit =>
              let
                fun take_abs 0 body = ([], body)
                  | take_abs n ((v, ty) `|=> (body, _)) =
                      take_abs (n - 1) body
                      |>> (fn binds => (IVar v, ty) :: binds)
                  | take_abs _ body = ([], body);
                val limited as (binds, _) = take_abs limit t;
              in
                if length binds = limit then limited
                else Code_Thingol.unfold_pat_abs t
              end);
        fun apply_eta_args body [] = body
          | apply_eta_args (ICase {term, typ, clauses, ...}) args =
              (* When the hidden tail of a function value is produced through a
                 case/if expression, distribute the eta arguments into each
                 branch.  The control-flow expression then returns the final
                 result type directly; its branches do not need to agree on a
                 concrete anonymous closure type before coercion to
                 `Rc<dyn Fn(..)>`. *)
              ICase {
                term = term,
                typ = typ,
                clauses = map (fn (pat, body) => (pat, apply_eta_args body args)) clauses,
                primitive = IVar NONE
              }
          | apply_eta_args body args = Library.foldl (op `$) (body, args)
        val (binds, t') =
          if not eta_tail then (binds0, body0)
          else (case term_type vars t of
            SOME ty =>
              let
                val (arg_tys, _) = fun_typs ty
                val missing_tys = drop (length binds0) arg_tys
              in
                if null missing_tys then (binds0, body0)
                else
                  let
                    val names =
                      Name.invent (rv_names vars |> snd) "eta_arg" (length missing_tys)
                    val eta_terms = map (IVar o SOME) names
                    (* Function values are erased to one uncurried `Rc<dyn Fn(..)>`
                       whose parameter list is derived from the full HOL function
                       type.  A lambda may expose only the first binder
                       syntactically and return the rest through control flow, e.g.
                       `%x. if c then (%y. ...) else (%y. ...)`.  Add the missing
                       type-level binders to this Rust closure and apply the
                       original body to them, so the closure arity matches the
                       already-printed `Fn(A, B) -> C` trait object type. *)
                    val eta_binds = ListPair.zip (eta_terms, missing_tys)
                    val body = apply_eta_args body0 eta_terms
                  in (binds0 @ eta_binds, body) end
              end
          | NONE => (binds0, body0));
        val (outer_namemap, outer_namectxt) = rv_names vars;
        val pat_vars = fold (Code_Thingol.add_varnames o fst) binds [];
        val body_free = Code_Thingol.add_varnames t' [];
        val captured_vars =
          filter (fn v =>
            Symtab.defined outer_namemap v
            andalso not (member (op =) pat_vars v)) body_free;
        val (cap_names, outer_namectxt') =
          fold_map Name.variant (map (fn v => v ^ "_cap") captured_vars) outer_namectxt;
        val outer_namemap' =
          fold2 (curry Symtab.update) captured_vars cap_names outer_namemap;
        val cap_tys =
          fold (fn v =>
            case Symtab.lookup (rv_types vars) v of
              SOME info => Symtab.update (v, info)
            | NONE => I) captured_vars (rv_types vars);
        val vars_capped = ((outer_namemap', outer_namectxt'), cap_tys);
        val effective_bind_shapes =
          (case bind_shapes of
            SOME shapes =>
              if length shapes = length binds
              then shapes else map (default_rust_shape o snd) binds
          | NONE => map (default_rust_shape o snd) binds);
        val (ps, vars') =
          fold_map (fn ((pat, ty), shape) =>
            print_bind_typed_shape is_pseudo_fun some_thm BR pat ty shape)
            (ListPair.zip (binds, effective_bind_shapes)) vars_capped;
        (* A representation adapter may change not only how adjacent arrows are
           grouped, but also the representation of a function-valued parameter.
           Print those boundary binders from their target Rust shapes so a wrapper
           over `A = X => Y` accepts the recursively unary instance type selected
           by A's dictionary, rather than reintroducing the flat itype spelling. *)
        val typs =
          map print_rust_shape effective_bind_shapes;
        val params =
          commas_append
            (map (fn (p1, p2) => Pretty.block [p1, str ": ", p2])
              (ListPair.zip (ps, typs)))
        val closure_body =
          print_term_expected body_expected is_pseudo_fun (false, box_new, clone)
            some_thm vars' NOBR t'
        (* A complete HOL function value is immediately erased to a
           `Rc<dyn Fn(..) -> T>` trait object.  State the same `T` on the Rust
           closure itself: a partial source match may lower to a body containing
           only `panic!`, whose inferred Output would otherwise remain the never
           type `!` and fail the trait-object coercion.  Immediate-callee closures
           (`eta_tail = false`) deliberately keep inference local to their call. *)
        val closure_return_type =
          if not eta_tail then NONE
          else
            Option.map (fn ty => print_typ NOBR (#2 (fun_typs ty)))
              (term_type vars t)
        (* Wrap in Rc::new so the closure value has the cloneable trait-object
           type Rc<dyn Fn(..)>. The unsizing coercion Rc<{anon}> -> Rc<dyn Fn>
           happens at the enclosing coercion site (function return, constructor
           argument, typed let); the return annotation above fixes only the
           closure's Output and does not replace that enclosing coercion. *)
        val closure_pretty = rust_closure params closure_return_type closure_body
      in
        (
          map2
            (fn v => fn vcap =>
              str ("let " ^ vcap ^ " = " ^ (rv_lookup_var vars v) ^ ".clone();"))
            captured_vars cap_names,
          closure_pretty
        )
      end
    and print_lambda_gen eta_tail is_pseudo_fun some_thm vars t =
      print_lambda_gen_limit eta_tail NONE is_pseudo_fun some_thm vars t
    and print_lambda_gen_limit eta_tail bind_limit is_pseudo_fun some_thm vars t =
      print_lambda_gen_limit_expected NONE NONE eta_tail bind_limit
        is_pseudo_fun some_thm vars t
    and print_lambda_gen_limit_expected body_expected bind_shapes eta_tail bind_limit
        is_pseudo_fun some_thm vars t =
      let
        val (cap_lets, closure_pretty) =
          print_lambda_parts_limit body_expected bind_shapes eta_tail bind_limit
            is_pseudo_fun some_thm vars t
        val closure_expr =
          if null cap_lets
          then closure_pretty
          else rust_bare_block (cap_lets @ [closure_pretty])
        (* A HOL abstraction emitted as a function VALUE uses the erased
           `Rc<dyn Fn(..)>` representation, including inside a tuple or one branch
           of a conditional.  Those expression positions do not always provide an
           enclosing expected type: without an explicit unsizing coercion Rust
           fixes `Rc::new(move |..| ..)` to `Rc<{anonymous closure}>`, so another
           branch containing an existing `Rc<dyn Fn(..)>` cannot unify with it.
           Cast the completed capture block to the abstraction's full HOL function
           type, keeping all branches on the same trait-object representation.

           An abstraction emitted as the IMMEDIATE callee of an application uses
           `eta_tail = false`: only its syntactic binders belong to that call, and
           the application printer supplies any remaining arguments separately.
           It must therefore retain the concrete closure type here rather than be
           coerced to the full type-level arrow chain. *)
        val coerced_closure =
          if not eta_tail then closure_expr
          else
            (case term_type vars t of
              SOME ty => rust_open
                [str "((", closure_expr, str ") as ", print_typ NOBR ty, str ")"]
            | NONE => closure_expr)
      in
        coerced_closure
      end
    and print_lambda_parts is_pseudo_fun some_thm vars t =
      print_lambda_parts_gen true is_pseudo_fun some_thm vars t
    and print_lambda is_pseudo_fun some_thm vars t =
      print_lambda_gen true is_pseudo_fun some_thm vars t;
    (** Print a `val name : typescheme` signature line. **)
    fun print_val_decl print_typscheme (sym, typscheme) = concat
      [str "val", str (deresolve sym), str ":", print_typscheme typscheme];
    (** Print a Rust enum declaration with #[derive(Clone)].
        Each constructor becomes an enum variant. **)
    fun print_datatype_decl definer (tyco, (vs, cos)) =
      let
        (* Phantom params of this datatype get a PhantomData<Ti> marker field in
           EVERY variant so the generic is used (Rust E0392). The table keeps this
           in lockstep with the markers emitted at construction/pattern sites. *)
        val phantoms = phantom_table (Type_Constructor tyco)
        val phantom_fields =
          map (fn v => str ("PhantomData<" ^ to_upper v ^ ">")) phantoms
        fun print_co ((co, _), []) =
              if null phantoms then str (deresolve_const co)
              else Pretty.block [
                str (deresolve_const co),
                str " ",
                rust_parens phantom_fields
              ]
          | print_co ((co, _), tys) =
            let
              (* Per-field Box<> from the precomputed table (one bool per field of
                 this constructor); falls back to no boxing on a length mismatch. *)
              val boxes = box_table (Constant co)
              val boxes' = if length boxes = length tys then boxes else map (K false) tys
              fun print_field (ty, needbox) =
                (if needbox then box else I) (print_typ (INFX (2, X)) ty)
              val data_fields = map print_field (ListPair.zip (tys, boxes'))
            in
              Pretty.block [
                str (deresolve_const co),
                str " ",
                rust_parens (data_fields @ phantom_fields)
              ]
            end;
      in
        Pretty.chunks [
          str "#[derive(Clone)]",
          rust_block
            (Pretty.block [
              str definer,
              Pretty.brk 1,
              print_tyco_expr (Type_Constructor tyco, map ITyVar vs)])
            (comma_lines (map print_co cos))
        ]
      end;
    (** Print a function definition.
        Emits an fn signature with generics, trait bounds, and either a direct
        expression, single-arm match, or multi-arm match body.
        impl_method: when SOME method_name, the function is emitted as a trait
        method inside an `impl` block (no `pub`, no generics, no where-clause —
        those live on the impl header) named method_name; when NONE it is a
        normal top-level `pub fn`. **)
    fun print_def is_pseudo_fun needs_typ definer impl_method
          (Function (const, (vs_ty as (vs, ty), eqs))) =
          let
            val is_impl = is_some impl_method
            fun to_tuple l prt = if (length l >= 2) then Pretty.block ([str "(", prt, str ")"]) else prt;
            (** Compute generic parameters <A, B> and where-clause trait bounds
                from the type variables and sort constraints. **)
            fun print_generics_and_traits vs ty =
              let
                fun extract_generics t =
                  let
                    fun aux (ITyVar v, acc) = to_upper v :: acc
                      | aux ((_ `%% tys), acc) = List.foldl aux acc tys
                  in aux (t, []) end
                val generic_params = distinct (op =) (extract_generics ty)
                fun print_traits vs generic_params = 
                  let
                    (* Every type parameter carries a `'static` bound: function
                       values are erased to `Rc<dyn Fn(..)>`, whose default object
                       lifetime is `'static`, so any captured type parameter must
                       outlive `'static` (E0310). In this owned-value model all
                       instantiations are owned and `'static`, so this is sound.
                       `'static` is emitted last so it follows the trait bounds. *)
                    fun print_vs_traits vs =
                      map
                      (fn (vname, sort) =>
                        Pretty.block(
                          str ((to_upper vname)^" : Clone")
                          :: (if List.null sort
                            then []
                            else [enum " +" " + " ""  (map (fn s => print_tyco_expr (Type_Class s, [])) sort)])
                          @ [str " + 'static"]
                        )
                      )
                      vs
                    val vl = map to_upper (map fst vs)
                    val other_traits =
                      map_filter
                      (fn s =>
                        if List.exists (fn s' => (s' = s)) vl
                        then NONE
                        else SOME (str (s^" : Clone + 'static")))
                      generic_params
                  in
                     (print_vs_traits vs) @ other_traits
                  end
              in
                pair
                (if List.null generic_params
                then []
                else [Pretty.brk 1, enum "," "<" ">" (map str generic_params)])
                (if List.null generic_params
                then []
                else print_traits vs generic_params)
              end;
            (* impl methods carry no generics/where-clause of their own; the bounds
               live on the surrounding impl header (printed by the Inst stmt). *)
            val (generics, trait_bounds) =
              if is_impl then ([], [])
              else print_generics_and_traits vs ty;
            (** Print a single equation as a match arm: "pattern => expr".
                If is_degenerated (single clause), prints just the expression body. **)
            fun print_eqn is_degenerated ((ts, t), (some_thm, _)) =
              let
                val typs = extract_typ (fn _ => fn ty => ty) ty
                val param_tys = take (length ts) typs
                val used_vars = build (Code_Thingol.add_varnames t)
                val ts' = map (wildcard_unused_pattern used_vars) ts
                val vars =
                  (reserved, Symtab.empty)
                  |> rv_intro_base_names_for (is_none o const_syntax)
                      deresolve (t :: ts)
                  |> rv_intro_typed_pats (ListPair.zip (ts, param_tys));
                val print_pattern_term = (print_term_pattern is_pseudo_fun some_thm vars NOBR)
                val print_expr_term = (print_term_app is_pseudo_fun some_thm vars NOBR)
              in
                if is_degenerated (*only 1 pattern clause in eqs*)
                then print_expr_term t
                else rust_arm
                  (to_tuple ts' (Pretty.block (commas_append (map print_pattern_term ts'))))
                  (print_expr_term t)
              end;
            fun print_eqn_body ((ts, t), (some_thm, _)) =
              let
                val typs = extract_typ (fn _ => fn ty => ty) ty
                val param_tys = take (length ts) typs
                val vars =
                  (reserved, Symtab.empty)
                  |> rv_intro_base_names_for (is_none o const_syntax)
                      deresolve (t :: ts)
                  |> rv_intro_typed_pats (ListPair.zip (ts, param_tys));
              in
                (case t of
                  (_ `|=> _) =>
                    let
                      val (cap_lets, closure_pretty) =
                        print_lambda_parts is_pseudo_fun some_thm vars t
                    in cap_lets @ [closure_pretty] end
                | ICase case_expr =>
                    let
                      fun default () = [print_term_app is_pseudo_fun some_thm vars NOBR t];
                      fun print_case_body () =
                        (case print_irrefutable_case_parts is_pseudo_fun
                            (false, box_new, clone) some_thm vars case_expr of
                          SOME (ps, body) => ps @ [body]
                        | NONE => default ())
                    in
                      (case Code_Thingol.unfold_const_app (#primitive case_expr) of
                        SOME ({sym = Constant const, ...}, _) =>
                          if is_none (const_syntax const) then print_case_body () else default ()
                      | _ => print_case_body ())
                    end
                | _ => [print_term_app is_pseudo_fun some_thm vars NOBR t])
              end;
            (** Print the function signature and body:
                generates dummy parameter names, type annotations, return type,
                and dispatches to direct expr / single match / multi match body. **)
            fun print_eqns prolog (vs_ty as (vs, ty)) is_pseudo eqs =
              let
                val vars0 = reserved
                  |> intro_base_names_for (is_none o const_syntax)
                      deresolve (map (snd o fst) eqs)
                fun eq_patterns_for_param_names ((ts, t), _) =
                  let val used_vars = build (Code_Thingol.add_varnames t)
                  in map (wildcard_unused_pattern used_vars) ts end
                val dummy_param_names =
                  (aux_params vars0 o map eq_patterns_for_param_names) eqs;
                val dummy_parms = map str dummy_param_names;
                (* Stable matching lowers one source pattern tuple into nested
                   Rust matches.  Reserve the signature parameter names in every
                   row context before introducing constructor-field binders;
                   otherwise a field such as `x1` may shadow the still-pending
                   parameter `x1`, and the next nested match observes the field's
                   type instead of the original argument's datatype. *)
                val vars0_with_params = intro_vars dummy_param_names vars0;
                val vars = (vars0_with_params, Symtab.empty);
                val typs = extract_typ print_typ ty
                val param_typs = List.take (typs, (List.length dummy_parms))
                val raw_ret_ty =
                  drop_fun_type (List.length dummy_parms) ty;
                val ret_shape =
                  (case function_result_rust_shape [] (Constant const) of
                    SOME shape =>
                      if shape_type shape = raw_ret_ty
                      then shape else default_rust_shape raw_ret_ty
                  | NONE => default_rust_shape raw_ret_ty);
                (* A function body's stable source shape is part of its Rust item
                   boundary.  Printing that shape on the signature lets a
                   dictionary-selected value remain nested even when it is wrapped
                   in a result constructor such as `Set`; ordinary definitions
                   still obtain exactly the default flat shape.  Call sites query
                   the same function_result_rust_shape helper, so the choice is not
                   local to this declaration. *)
                val ret_typ = print_rust_shape ret_shape
                val dummy_parms_with_typs = ListPair.zip (dummy_parms, param_typs)
                  |> map (fn (prt1, prt2) => Pretty.block ([prt1, str ": ", prt2]))
                fun is_var_pattern (IVar _) = true
                  | is_var_pattern _ = false
                fun eq_has_boxed_patterns ((ts, _), _) =
                  exists pat_contains_boxed_field ts;
                fun print_stable_eqns eqs =
                  let
                    val raw_typs = extract_typ (fn _ => fn ty => ty) ty;
                    val param_raw_typs = List.take (raw_typs, List.length dummy_parms);
                    val columns = ListPair.zip (dummy_parms, param_raw_typs);
                    fun row ((ts, t), (some_thm, _)) =
                      let
                        val param_tys = take (length ts) raw_typs;
                        val vars =
                          (vars0_with_params, Symtab.empty)
                          |> rv_intro_base_names_for (is_none o const_syntax)
                              deresolve (t :: ts)
                          |> rv_intro_typed_pats (ListPair.zip (ts, param_tys));
                        val used_vars = build (Code_Thingol.add_varnames t);
                      in
                        (ts, vars, used_vars, [],
                          print_term_app is_pseudo_fun some_thm vars NOBR t)
                      end;
                  in
                    stable_match_compile is_pseudo_fun NONE vars
                      columns (map row eqs)
                      (str "panic!(\"non-exhaustive match\")")
                  end;
                val sig_head =
                  Pretty.block [
                    prolog,
                    Pretty.brk_indent 1 2,
                    enum "," "(" ")" dummy_parms_with_typs,
                    str " -> ",
                    ret_typ
                  ]
                val scrutinee = to_tuple dummy_parms ((Pretty.block o commas) dummy_parms)
                val body =
                  (case eqs
                    of [eq as ((ts, t), _)] =>
                        if List.all is_var_pattern ts
                        then Pretty.chunks (print_eqn_body eq)
                        else if eq_has_boxed_patterns eq
                        then print_stable_eqns [eq]
                        else rust_match scrutinee
                          [print_eqn false eq,
                           rust_arm (str "_") (str "panic!(\"non-exhaustive match\")")]
                     | _ =>
                        (* catch-all: HOL functions may be partial, but Rust matches
                           must be total (e.g. `nth [] n` has no clause). *)
                        if exists eq_has_boxed_patterns eqs
                        then print_stable_eqns eqs
                        else
                          rust_match scrutinee
                            (map (print_eqn false) eqs
                              @ [rust_arm (str "_") (str "panic!(\"non-exhaustive match\")")]))
              in
                rust_fn sig_head trait_bounds [body]
              end;
            val prolog =
              case impl_method
               of NONE =>
                    Pretty.block ([str ("pub "^definer), Pretty.brk 1,
                      (str o deresolve_const) const] @ generics)
                | SOME method_name => Pretty.block [str definer, Pretty.brk 1, str method_name]
          in pair
            (print_val_decl print_typscheme (Constant const, vs_ty))
            (print_eqns prolog vs_ty (is_pseudo_fun (Constant const)) eqs)
          end;
    (** Render one reconstructed `impl Trait for Type { .. }` block.
        Factored out of the Inst printer so InstGroup can emit several impls in a
        single statement slot (see the InstGroup datatype comment). **)
    fun print_inst_impl ((class, tyco), (vs, methods)) =
          let
            (** "impl<A : Clone + Bound, ..> Class for Tyco<A, ..>" header. **)
            val header = Pretty.block [
              str "impl",
              if null vs then str "" else Pretty.brk 1,
              print_impl_generics vs,
              Pretty.brk_indent 1 2,
              str (deresolve_class class),
              str " for",
              Pretty.brk_indent 1 2,
              print_tyco_expr (Type_Constructor tyco, map (ITyVar o fst) vs)
            ]
            fun subst_self_type self_var self_ty (ITyVar v) =
                  if v = self_var then self_ty else ITyVar v
              | subst_self_type self_var self_ty (tyco `%% tys) =
                  tyco `%% map (subst_self_type self_var self_ty) tys;
            fun method_type classparam =
              (case lookup_class_methods class of
                SOME (self_var, cps) =>
                  Option.map (fn mty =>
                    let
                      val self_ty = tyco `%% map (ITyVar o fst) vs;
                    in (subst_self_type self_var self_ty mty, arrow_arity mty) end)
                    (AList.lookup (op =) cps classparam)
              | NONE => NONE);
            (** Fetch and eta-normalize the implementing constant's equations
                from the (untouched) program, so its body can be inlined as the
                trait method.
                The trait declares this method from the class parameter type, with
                the class variable substituted by the instance Self type.  That
                distinction matters for instances at HOL `fun`: a class value
                method such as `unit_pt :: 'a` returns `Self`, and if `Self` is a
                function value it must print as one Rust return type
                `Rc<dyn Fn(..)>`, not as extra method parameters.  Eta-expansion is
                therefore bounded by the class parameter's declared arity, while
                the instantiated class-parameter type supplies the Rust signature. **)
            fun normalize_method_eq mty target ((ts, t), some_thm) =
              let
                val delta = target - length ts;
              in
                if delta > 0 then
                  let
                    val newvars =
                      List.tabulate (delta, fn i =>
                        IVar (SOME ("eta_arg_" ^ string_of_int i)))
                  in
                    ((ts @ newvars,
                      fold (fn v => fn body => body `$ v) newvars t), some_thm)
                  end
                else if delta < 0 then
                  let
                    val extra = ~delta;
                    val (method_ts, value_ts) = chop target ts;
                    val (arg_tys, ret_ty) = fun_typs mty;
                    val value_tys = take extra (drop target arg_tys);
                    fun varname (IVar v) = SOME v
                      | varname _ = NONE;
                    val value_vars = map_filter varname value_ts;
                    (* Pointwise equations for a function-type instance expose
                       the function domain as trailing LHS variables, although
                       the class method returns that entire function as Self.
                       Fold those variables back into a lambda so only the class
                       parameter's own arguments remain Rust method parameters.
                       Non-variable trailing patterns retain their original form;
                       contracting those would require a pattern match inside the
                       returned closure and is not a pointwise instance equation. *)
                  in
                    if length value_vars = extra
                    then ((method_ts,
                      (ListPair.zip (value_vars, value_tys)) `|==> (t, ret_ty)),
                      some_thm)
                    else ((ts, t), some_thm)
                  end
                else ((ts, t), some_thm)
              end;
            fun method_function classparam const_sym =
              case (lookup_constant_fun const_sym, method_type classparam)
               of (SOME ((_, raw_eqs), _), SOME (mty, target)) =>
                    let
                      val eqs = filter (snd o snd) raw_eqs
                    in SOME ((vs, mty), map (normalize_method_eq mty target) eqs) end
                | (SOME ((tysm as (_, mty), raw_eqs), _), NONE) =>
                    let
                      val eqs = filter (snd o snd) raw_eqs
                      val target = arrow_arity mty
                    in SOME (tysm, map (normalize_method_eq mty target) eqs) end
                | _ => NONE
            fun print_method (classparam, method_sym) =
              let
                val const_s = (fn Constant s => s | sym => deresolve sym) method_sym
                (* A method name inside `impl Trait for T { fn .. }` must be the
                   bare trait-method name, never crate-qualified. *)
                val method_name = deresolve_base (Constant classparam)
              in
                case method_function classparam method_sym
                 of SOME fb =>
                      snd (print_def (K false) false "fn" (SOME method_name) (Function (const_s, fb)))
                  | NONE => str ("/* unresolved instance method "^method_name^" */")
              end
            (** Fill in the class methods this instance does not code-generate as a
                `Fun`. Two cases:
                * the method is realised by a nullary data constructor (e.g.
                  `0::int`): emit `fn m(..) -> Self { Tyco::Variant }`, taking the
                  constructor from `constr_method_of`;
                * otherwise Isabelle simply did not emit it (only methods reachable
                  from the export root are generated, e.g. word uses only a subset
                  of semiring_bit_operations). Rust still requires every trait
                  method, so emit `fn m(..) -> Self { panic!(..) }`; being
                  unreachable, the panic is dead.
                The signature is taken from the class's classparam type with the
                class type variable mapped to Self. **)
            (* An instance method whose implementing constant carries NO code
               equation (e.g. topology's non-executable `open` for the product
               space: `open_prod` has eqs=[]) cannot be printed as a `fn` body --
               print_eqns -> Code_Printer.aux_params does `hd []` and raises Empty.
               Treat it exactly like a method Isabelle never emitted: drop it from
               the real methods so the stub path below fills it with a panic stub
               of the right signature. *)
            fun method_has_body (classparam, method_sym) =
              (case method_function classparam method_sym of SOME (_, eqs) => not (null eqs) | NONE => false)
            val real_methods = filter method_has_body methods
            val provided_cps = map fst real_methods
            val stub_methods =
              (case lookup_class_methods class of
                  NONE => []
                | SOME (cls_v, all_cps) =>
                    map_filter (fn (cp, mty) =>
                      if member (op =) provided_cps cp then NONE
                      else
                        let
                          val nm = deresolve_base (Constant cp)
                          val tail =
                            (case constr_method_of cp tyco of
                                SOME csym =>
                                  [str (" { " ^ tyco_name_str tyco
                                        ^ "::" ^ deresolve_base csym ^ " }")]
                              | NONE =>
                                  [str (" { panic!(\"unimplemented instance method: "
                                        ^ nm ^ "\") }")])
                        in SOME (print_method_sig nm mty cls_v tail) end)
                      all_cps)
          in
            rust_block header (map print_method real_methods @ stub_methods)
          end;
    (** Top-level statement dispatcher: routes each stmt variant to its printer.
        Exc -> exception stub, Val -> single binding, Funs -> function group,
        Datas -> enum declarations, Class -> trait declaration, Inst -> impl block. **)
    (*fun print_stmt: Code_Namespace.export -> stmt -> Pretty.T list * Pretty.T*)
     fun print_stmt _ (Exc (const, (vs_ty as (vs, ty), n))) =
          let
            val typs = extract_typ print_typ ty
            val param_typs = take n typs
            val ret_typs = drop n typs
            val ret_typ = (case ret_typs
              of [] => str "!"
              | [t] => t
              | ts =>
                  let
                    val ret = List.last ts
                    val params = List.take (ts, ((List.length ts) - 1))
                  in rc_dyn_fn params ret end)
            val params =
              map_index (fn (i, ty) =>
                Pretty.block [str ("x" ^ Int.toString i ^ ": "), ty]) param_typs
            fun print_vs_trait (vname, sort) =
              Pretty.block(
                str ((to_upper vname)^" : Clone")
                :: (if List.null sort
                  then []
                  else [enum " +" " + " "" (map (fn s => print_tyco_expr (Type_Class s, [])) sort)])
                @ [str " + 'static"])
            val generics =
              if List.null vs then str ""
              else enum "," "<" ">" (map (str o to_upper o fst) vs)
            val trait_bounds =
              if List.null vs then [] else map print_vs_trait vs
            val sig_head =
              Pretty.block [
                str "pub fn ",
                str (deresolve_const const),
                generics,
                enum "," "(" ")" params,
                str " -> ",
                ret_typ
              ]
          in pair
            [print_val_decl print_typscheme (Constant const, vs_ty)]
            (rust_fn sig_head trait_bounds
              [Pretty.block [str "panic!(", str (print_rust_string const), str ")"]])
          end
      | print_stmt _ (Val binding) =
          let
            val (sig_p, p) = print_def (K false) true "fn" NONE binding
          in pair
            [sig_p]
            (p)
          end
      | print_stmt _ (Funs ((export, binding) :: exports_bindings, pseudo_funs)) =
          let
            val print_def' = (fn definer => print_def (member (op =) pseudo_funs) false definer NONE);
            (* A self-referential nullary value cannot be represented by the eager
               owned Rust model.  Emitting it as `fn x() { ... x() ... }` would
               diverge while constructing productive codatatypes, while the former
               item-level `let x = x();` was not valid Rust at all.  Reject this
               unsupported semantic boundary instead of producing a crate that is
               either ill-formed or observably wrong. *)
            val _ =
              if null pseudo_funs then ()
              else error ("Rust target does not support self-referential nullary values: " ^
                String.concatWith ", " (map deresolve pseudo_funs));
            val head = "fn";
            val (sig_ps, (ps, p)) = (apsnd split_last o split_list)
              (print_def' head binding :: map (print_def' head o snd) exports_bindings);
          in pair
            (map_filter (fn (export, p) => if Code_Namespace.not_private export then SOME p else NONE)
              ((export :: map fst exports_bindings) ~~ sig_ps))
            (Pretty.chunks2 (ps @ [p]))
          end
     | print_stmt export (Datas [(tyco, (vs, []))]) =
          (* A datatype with no code-generated constructors (an abstract type such
             as Word_Lib's `'a signed`). It has no runtime representation here and
             is only ever used as a phantom/length marker inside other phantom
             types, yet it still needs to be a nominal type so it can carry impls
             (e.g. `impl Len0 for Signed<A>`). Emit a unit/phantom struct: a
             `type _ = EMPTY__` alias would be an undefined-type parse error, and a
             plain generic struct would trip E0392 on the unused params. *)
          let
            val head = if Code_Namespace.not_private export then "pub struct" else "struct";
            val ty_p = print_tyco_expr (Type_Constructor tyco, map ITyVar vs);
            val phantom_fields = map (fn v => str ("PhantomData<" ^ to_upper v ^ ">")) vs;
            val decl =
              Pretty.chunks [
                str "#[derive(Clone)]",
                if null vs
                then concat [str head, ty_p, str ";"]
                else Pretty.block [str head, Pretty.brk 1, ty_p,
                       str "(", enum "," "" "" phantom_fields, str ");"]
              ]
          in
            pair [concat [str "type", ty_p]] decl
          end
     | print_stmt export (Datas (datas)) = 
          let
            val head = (if Code_Namespace.not_private export then "pub enum" else "enum");
            val decl_ps = map (print_datatype_decl head) datas;
            val (ps, p) = split_last decl_ps;
          in pair
            (if Code_Namespace.is_public export
              then decl_ps
              else map (fn (tyco, (vs, _)) =>
                concat [str "type", print_tyco_expr (Type_Constructor tyco, map ITyVar vs)])
                (datas))
            (Pretty.chunks (ps @| p))
          end
     | print_stmt export (Class (class, (v, (classrels, classparams)))) =
          let
            fun print_super_traits classrels =
              if (List.length classrels) = 0 then str ""
              else enum " +" " : " ""  (map (fn s => print_dicttyp (s, ITyVar "_")) (map snd classrels))
            fun print_trait_method (class, ty) =
              print_trait_typ class ty v
            val trait_decl_p =
              rust_block
                (Pretty.block [
                  str "pub trait ",
                  print_dicttyp (class, ITyVar v),
                  print_super_traits classrels])
                (map print_trait_method classparams)
            (** A class with no parameters is an empty marker trait (only a bundle
                of superclasses). Isabelle knows which types inhabit it but emits
                no instance methods, so the per-type `impl` is never reconstructed
                and `T: Marker` bounds go unsatisfied (E0277; some nightly rustc
                even ICEs on the unsatisfied supertrait of another impl). Emit one
                blanket impl `impl<T: supers> Marker for T {}` instead: it holds
                for exactly the types meeting the superclass bounds, and cannot
                clash with any explicit impl (empty traits are never reconstructed
                as one). **)
            val blanket_impl_p =
              if null classparams
              then SOME (Pretty.block [
                     str "impl<T",
                     print_super_traits classrels,
                     str "> ",
                     str (deresolve_class class),
                     str " for T {}"])
              else NONE
            val body_p =
              case blanket_impl_p
                of SOME bi => Pretty.chunks2 [trait_decl_p, bi]
                 | NONE => trait_decl_p
          in pair
           (if Code_Namespace.is_public export
              then [trait_decl_p]
              else if null classrels andalso null classparams
              then [trait_decl_p] (*work around weakness in export calculation*)
              else [concat [str "type", print_dicttyp (class, ITyVar v)]])
          body_p
          end
     | print_stmt _ (Inst inst) = pair [] (print_inst_impl inst)
       (* Emit every bundled closure impl into this single statement slot
          (see the InstGroup datatype comment for why they are bundled). *)
     | print_stmt _ (InstGroup insts) =
          pair [] (Pretty.chunks2 (map print_inst_impl insts));
  in print_stmt end;

(** print module **)

(** Print a Rust module: prepend `use` statements to the body.
    `includes` are external crates, imported with a glob (`use num_bigint::*;`).
    `crate_uses` are explicit crate-internal item paths, emitted only when the
    short imported name is unambiguous inside this module. Other cross-module
    references remain fully `crate::`-qualified at their use sites. **)
fun print_rust_module name decls crate_uses includes body =
  let
    (* Import the BigInt support crates (num_bigint / num_traits::sign) only for
       files that actually use BigInt, so the `use ...::*;` globs stay out of
       files that map integers nowhere. The optional BigInt setup theories and
       numeral literals both surface the substring "BigInt", so a per-file body
       scan covers every use site. *)
    val bigint_includes = ["num_bigint", "num_traits::sign"]
    val uses_bigint =
      List.exists (fn p => String.isSubstring "BigInt" (Pretty.string_of p)) body
    val includes' =
      if uses_bigint then includes
      else filter_out (member (op =) bigint_includes) includes
    (* num_traits::sign is needed only for the `Signed::abs` method (BigInt
       div/mod). Import the trait ANONYMOUSLY (`as _`) rather than glob-importing
       it: a generated phantom-type marker `struct Signed<..>` (signed words) would
       otherwise shadow `num_traits::sign::Signed` and hide `.abs()` (E0599). *)
    val includes_p = Pretty.chunks (map (fn i =>
        if i = "num_traits::sign"
        then str "use num_traits::sign::Signed as _;"
        else str ("use "^i^"::*;")) includes')
    val crate_uses_p = Pretty.chunks (map (fn p => str ("use "^p^";")) crate_uses)
    (* Import std::marker::PhantomData only for files that actually emit a phantom
       marker, so the short `PhantomData` form stays valid without polluting other
       files. Detection is per-file: it also covers construction/pattern sites in
       a module other than the datatype's declaring module. *)
    val uses_phantom =
      List.exists (fn p => String.isSubstring "PhantomData" (Pretty.string_of p)) body
    (* Import Rc only for files that materialise a function value or type as
       Rc<dyn Fn(..)> (HOL function types -> cloneable trait objects). Both the
       type `Rc<` and the constructor `Rc::new` surface the substring, covering
       declaration and value sites. *)
    val uses_rc =
      List.exists (fn p =>
        let val s = Pretty.string_of p
        in String.isSubstring "Rc<" s orelse String.isSubstring "Rc::" s end) body
    val headers =
      (if List.null includes' then [] else [includes_p])
      @ (if List.null crate_uses then [] else [crate_uses_p])
      @ (if uses_phantom then [str "use std::marker::PhantomData;"] else [])
      @ (if uses_rc then [str "use std::rc::Rc;"] else [])
  in
    Pretty.chunks2 (headers @ body)
  end

(** Literal syntax definitions for Rust target (strings, numerals, lists, cons). **)
val literals_rust = let
  fun int_to_bytes k =
    let
      fun aux 0 acc = if acc = [] then [0] else acc
        | aux n acc = aux (n div 256) (n mod 256 :: acc)
    in
      aux k []
    end
  fun numeral_rust k =
    if k < 0 then
      "-" ^ numeral_rust (~k)
    else 
      let
        val bytes = int_to_bytes k
        val byte_str = String.concatWith ", " (List.map Int.toString bytes)
      in
        "BigInt::from_bytes_be(Sign::Plus, &[" ^ byte_str ^ "])"
      end
in Literals {
  literal_string = print_rust_string,
  literal_numeral = numeral_rust,
  literal_list = enum ";" "[" "]",
  infix_cons = (6, "::")
} end;

(** namify **)

(** Name variant generators: enforce Rust naming conventions.
    Functions get snake_case, types and constructors get UpperCamelCase. **)
fun variant_snake_case s ctxt =
    ctxt |> Name.variant (to_snake_case s)

fun variant_upper_camel_case s ctxt =
    ctxt |> Name.variant (to_upper_camel_case s)

(** Transform Code_Thingol program into Rust-specific stmt IR.
    Handles naming conventions (snake_case for fns, CamelCase for types),
    converts Thingol statements to the local binding/stmt datatypes,
    and builds the hierarchical module structure via Code_Namespace. **)
fun rust_program_of_program ctxt module_name reserved identifiers
    (inst_method_syms, inst_table) operational_function_vs
    closure_inst_data orphan_closure_hosts =
  let
    (** A constant that implements a polymorphic instance method: its body is
        inlined into the generated impl block (see the Inst printer), so it must
        not be emitted as a standalone top-level function. **)
    fun is_inst_method sym = member (op =) inst_method_syms sym;
    (** If sym is the chosen representative of an instance, the Inst stmt to emit
        in its place (carrying every method of that instance). **)
    fun repr_inst sym = AList.lookup (op =) inst_table sym;
    (** An external Rust type has no datatype statement where its missing
        superclass implementations can be emitted.  Its closure implementations
        are therefore attached to exactly one reconstructed instance representative.
        Replacing that representative's single Inst with one InstGroup preserves
        Code_Namespace's one-output-slot-per-input invariant while keeping every
        impl in the module that already owns the external type's explicit impl. **)
    fun emit_inst export sym data =
      (case AList.lookup (op =) orphan_closure_hosts sym of
          NONE => SOME (export, Inst data)
        | SOME closure_insts => SOME (export, InstGroup (data :: closure_insts)));
    fun namify_const variant base (nsp_const, nsp_type) =
      let
        val (base', nsp_const') = variant base nsp_const
      in (base', (nsp_const', nsp_type)) end;
    fun namify_type variant base (nsp_const, nsp_type) =
      let
        val (base', nsp_type') = variant base nsp_type
      in (base', (nsp_const, nsp_type')) end;
    (** Assign Rust naming conventions per statement kind. **)
    fun namify_stmt (Code_Thingol.Fun _) = namify_const variant_snake_case
      | namify_stmt (Code_Thingol.Datatype _) = namify_type variant_upper_camel_case
      | namify_stmt (Code_Thingol.Datatypecons _) = namify_const variant_upper_camel_case
      | namify_stmt (Code_Thingol.Class _) = namify_type variant_upper_camel_case
      | namify_stmt (Code_Thingol.Classrel _) = namify_const variant_upper_camel_case
      | namify_stmt (Code_Thingol.Classparam _) = namify_const variant_snake_case
      | namify_stmt (Code_Thingol.Classinst _) = namify_const variant_upper_camel_case;
    (** Convert a Thingol Fun statement into a Function binding.
        Also detects eta-expanded constants and self-referential values. **)
    fun binding_of_stmt (sym as Constant const, (export, Code_Thingol.Fun (((vs, ty), raw_eqs), _))) =
          let
            val tysm' = (operational_function_vs sym vs, ty);
            val eqs = filter (snd o snd) raw_eqs;
            val (eqs', some_sym) = if null (filter_out (null o snd) vs) then case eqs
               of [(([], t), some_thm)] => if (not o null o fst o Code_Thingol.unfold_fun) ty
                  then ([(([IVar (SOME "x")], t `$ IVar (SOME "x")), some_thm)], NONE)
                  else (eqs, SOME (sym, member (op =) (Code_Thingol.add_constsyms t []) sym))
                | _ => (eqs, NONE)
              else (eqs, NONE)
          in ((export, Function (const, (tysm', eqs'))), some_sym) end
      | binding_of_stmt (sym, _) =
          error ("Binding block containing illegal statement: " ^
            Code_Symbol.quote ctxt sym)
    (** For a group of statements, emit one Inst (impl block) for each instance
        whose representative constant appears in the group. **)
    fun emit_insts stmts =
      map_filter (fn (sym, (export, _)) =>
        Option.map (emit_inst export sym) (repr_inst sym)) stmts;
    (** Drop case combinators and instance-method functions (the latter are
        inlined into their impl block by the Inst printer). **)
    fun keep_normal stmts =
      filter_out (fn (sym, (_, stmt')) =>
        Code_Thingol.is_case stmt' orelse is_inst_method sym) stmts;
    (** Convert a single Fun into a stmt: Exc (no equations), Val, or Funs. **)
    fun modify_fun (sym, (export, stmt)) =
      let
        val ((export', binding), some_value_sym) = binding_of_stmt (sym, (export, stmt));
        val stmt = case binding
         of Function (const, ((vs, ty), [])) =>
              Exc (const, ((vs, ty),
                (length o filter_out (null o snd)) vs + (length o fst o Code_Thingol.unfold_fun) ty))
          | _ => case some_value_sym
             of NONE => Funs ([(export', binding)], [])
              | SOME (sym, true) => Funs ([(export, binding)], [sym])
              | SOME (_, false) => Val binding
      in SOME (export, stmt) end;
    (** Convert a group of mutually recursive functions into a single Funs stmt.
        Only Fun members become bindings; any non-Fun that ended up in a Fun-led
        SCC is skipped rather than aborting the whole serialization with an error. **)
    fun modify_funs stmts =
      let
        val funs = filter (fn (_, (_, Code_Thingol.Fun _)) => true | _ => false) stmts
      in
        if null funs then []
        else single (SOME
          (Code_Namespace.Opaque, Funs (map_split binding_of_stmt funs |> (apsnd o map_filter o Option.map) fst)))
      end;
    (** Collect Datatype statements into a single Datas stmt (multi-constructor enum). **)
    fun modify_datatypes stmts =
      let
        val datas = map_filter
          (fn (Type_Constructor tyco, (export, Code_Thingol.Datatype stmt)) => SOME (export, (tyco, stmt)) | _ => NONE) stmts
        (* Emit this group's missing superclass-closure impls right beside its
           datatypes.  A datatype is declared in exactly one group, so this needs
           no cross-group de-duplication; closure_inst_data is already distinct.
           Types rendered by external code_printing syntax have no Datas statement
           and are instead attached to an explicit instance by emit_inst above.
           They are bundled into ONE InstGroup statement rather than one Inst each:
           Code_Namespace.hierarchical_program forbids modify_stmts from returning
           more entries than it received, and a small datatype group (e.g.
           single-constructor `RBT.rbt` needing two closures) has fewer input syms
           than it would produce as separate impls.  Bundling caps the group's
           output at two statements (Datas + InstGroup). *)
        val closure_insts =
          maps (fn (_, (tyco, _)) =>
            map_filter (fn (cls, t, vs) =>
              if t = tyco then SOME ((cls, t), (vs, [])) else NONE)
              closure_inst_data)
            datas
        val closure_stmts =
          if null closure_insts then []
          else [SOME (Code_Namespace.join_exports (map fst datas), InstGroup closure_insts)]
      in
        if null datas then [] (*for abstract types wrt. code_reflect*)
        else (datas
          |> split_list
          |> apfst Code_Namespace.join_exports
          |> apsnd Datas
          |> SOME
          |> single) @ closure_stmts
      end;
    (** Collect the Class node of a class SCC into a single Class stmt (trait).
        The Code_Thingol.Class node already carries the superclass relations and
        the class parameters, so the separate Classrel/Classparam members of the
        SCC are redundant and dropped. A group that happens to carry no Class node
        (its trait is emitted from the Class node living in another SCC) yields
        nothing, rather than crashing the_single on an empty list. **)
    fun modify_class stmts =
      (case map_filter
              (fn (Type_Class class, (export, Code_Thingol.Class stmt)) => SOME (export, (class, stmt))
                | _ => NONE)
              stmts of
        [] => []
      | (class_stmt :: _) => [SOME (apsnd Class class_stmt)]);
    (** Dispatch statement groups by kind to the appropriate modify_* handler.
        Filters out case combinators from function stmts. **)
    fun modify_stmts ([stmt as (sym, (export, stmt' as Code_Thingol.Fun _))]) =
          if Code_Thingol.is_case stmt' then []
          else if is_inst_method sym
          then (case repr_inst sym of SOME data => [emit_inst export sym data] | NONE => [])
          else [modify_fun stmt]
      | modify_stmts (stmts as ((_, (_, Code_Thingol.Fun _)) :: _)) =
          let val normal = keep_normal stmts
          in emit_insts stmts @ (if null normal then [] else modify_funs normal) end
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Datatypecons _)) :: _)) =
          modify_datatypes stmts
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Datatype _)) :: _)) =
          modify_datatypes stmts
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Class _)) :: _)) =
          modify_class stmts
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Classrel _)) :: _)) =
          modify_class stmts
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Classparam _)) :: _)) =
          modify_class stmts
      | modify_stmts (stmts as ((_, (_, Code_Thingol.Classinst _)) :: _)) =
          (* Isabelle eliminates Classinst before serialization in this toolchain;
             any that survive carry no Rust-level content, so drop them. *)
          map (K NONE) stmts
      | modify_stmts stmts = error ("Illegal mutual dependencies: " ^
          (Library.commas o map (Code_Symbol.quote ctxt o fst)) stmts);
  in
    Code_Namespace.hierarchical_program ctxt {
      module_name = module_name, reserved = reserved, identifiers = identifiers,
      empty_nsp = (reserved, reserved), namify_module = pair, namify_stmt = namify_stmt,
      (* Rust modules may reference each other freely (cross-module refs are
         emitted as fully-qualified `crate::Mod::name` paths), so mutually
         recursive modules are legal -- unlike OCaml. Allowing cycles is required
         once numeric types are code_printing-mapped (e.g. nat/int -> BigInt):
         the reconstructed `impl Zero/One for int` instances land in the Arith
         module while their trait/superclass relations live elsewhere, which the
         acyclic check would otherwise reject (zero_neq_one < one cycle). *)
      cyclic_modules = true, class_transitive = true,
      class_relation_public = true, empty_data = (),
      memorize_data = K I, modify_stmts = modify_stmts }
  end;

(** Top-level serializer: orchestrates the full translation pipeline.
    1. Builds the hierarchical Rust program IR from Thingol
    2. Constructs global lookup functions (recursive types, constructors, classes)
    3. Computes module-level import dependencies
    4. Prints each statement via print_rust_stmt
    5. Assembles Cargo.toml, main.rs, and per-module .rs files **)
fun serialize_rust rust_module rust_version rust_edition rust_dependencies rust_lints rust_includes
    print_rust_module print_rust_stmt rust_extension ctxt
    { module_name, reserved_syms, identifiers, includes,
      class_syntax = _, tyco_syntax, const_syntax } program exports =
  let
    val stmt_list = (Code_Symbol.Graph.dest program)
    val sym_dpdnc_list = map (fn ((sym, _), children) => (sym, children)) stmt_list


    val rust_module = if rust_module = "" then "\"isabelle_exported\"" else rust_module;
    val rust_version = if rust_version = "" then "\"0.1.0\"" else rust_version;
    val rust_edition = if rust_edition = "" then "\"2024\"" else rust_edition;
    val rust_dependencies = if rust_dependencies = "" then "num-bigint = \"0.4.6\"\nnum-traits = \"0.2.19\"" else rust_dependencies;
    val rust_lints = if rust_lints = "" then "unused = \"allow\"\nnonstandard_style = \"allow\"\nunreachable_patterns = \"allow\"" else rust_lints;

    val rust_includes = "num_bigint" :: "num_traits::sign" :: rust_includes

    (* Reconstruct type-class instances from the specialized projection functions
        Isabelle leaves behind after dictionary elimination. *)
    val inst_methods =
      let
        fun after_last_dot s =
          (case List.rev (String.fields (fn c => c = #".") s) of [] => s | x :: _ => x);
        fun before_last_dot s =
          (case List.rev (String.fields (fn c => c = #".") s) of x1 :: x2 :: _ => x2 | _ => s);
        fun tycos_of (ITyVar _) = []
          | tycos_of (tyco `%% tys) = tyco :: maps tycos_of tys;
        fun class_classparams cls =
          (case Code_Symbol.Graph.get_node program (Type_Class cls) of
              Code_Thingol.Class (_, (_, cps)) => cps
            | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        (* Every type class declared in this program. We match a projection
           function to its instance by the `<class>_<tyco>_inst` segment of its
           name, tested against all classes: a method's sort-context vs need not
           mention the instantiated class (it is empty for a monomorphic instance
           and may be omitted for a lifting instance), so vs is not a usable filter. *)
        val all_classes =
          distinct (op =) (map_filter (fn ((s, st), _) =>
            case (s, st) of
              (Type_Class c, Code_Thingol.Class _) => SOME c
            | _ => NONE) stmt_list);
        (* Executable code equations can require dictionaries that do not occur
           in the logical class method's type.  Function strict order is the
           canonical example: the instance signature says `B: Order`, while its
           executable inequality test calls HOL.equal and carries a Thingol
           `Dict_Var` for `B: Equal`.  Rust type-checks every emitted method body,
           so retain those operational dictionaries in the reconstructed impl
           header instead of relying only on the method typescheme's sorts. *)
        fun add_dict (Code_Thingol.Dict (_, plain)) bounds =
              add_plain_dict plain bounds
        and add_plain_dict (Code_Thingol.Dict_Const (_, dss)) bounds =
              fold (fn (_, ds) => fold add_dict ds) dss bounds
          | add_plain_dict (Code_Thingol.Dict_Var {var, class, ...}) bounds =
              insert (op =) (var, class) bounds;
        fun add_term_dicts (IConst {dicts, ...}) bounds =
              fold (fold add_dict) dicts bounds
          | add_term_dicts (IVar _) bounds = bounds
          | add_term_dicts (t1 `$ t2) bounds =
              bounds |> add_term_dicts t1 |> add_term_dicts t2
          | add_term_dicts (_ `|=> (body, _)) bounds =
              add_term_dicts body bounds
          | add_term_dicts (ICase {term, clauses, primitive, ...}) bounds =
              bounds
              |> add_term_dicts term
              |> add_term_dicts primitive
              |> fold (fn (pat, body) =>
                   add_term_dicts pat #> add_term_dicts body) clauses;
        fun method_body_bounds sym =
          (case Code_Symbol.Graph.get_node program sym of
            Code_Thingol.Fun ((_, raw_eqs), _) =>
              fold (fn ((ts, body), (_, active)) =>
                if active
                then fold add_term_dicts ts #> add_term_dicts body
                else I) raw_eqs []
          | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        fun add_method_body_bounds sym vs =
          fold (fn (v, class) =>
            map (fn (v', sort) =>
              if v = v' then (v', insert (op =) class sort)
              else (v', sort)))
            (method_body_bounds sym) vs;
      in
        map_filter (fn ((sym, stmt), _) =>
          case (sym, stmt) of
            (Constant const, Code_Thingol.Fun (((vs, ty), _), _)) =>
              let
                val candidate_classes = all_classes
              in
                if null candidate_classes then NONE
                else
                  let
                    val typcons = distinct (op =) (tycos_of ty)
                    val inst_s = before_last_dot const
                    fun matches cls tyc =
                      (after_last_dot cls ^ "_" ^ after_last_dot tyc ^ "_inst") = inst_s
                    val hit = get_first (fn cls =>
                      get_first (fn tyc => if matches cls tyc then SOME (cls, tyc) else NONE) typcons)
                      candidate_classes
                  in
                    case hit of
                      NONE => NONE
                    | SOME (cls, tyc) =>
                        let
                          val cps = class_classparams cls
                          val vs' = add_method_body_bounds sym vs
                          (* Require const = `<classparam>_<tyco>` even for a
                             single-method class, so an auxiliary function that
                             merely shares the `<class>_<tyco>_inst` segment is
                             not mistaken for the method. *)
                          val cp_opt =
                            Option.map fst (find_first (fn (cp, _) =>
                              after_last_dot const = after_last_dot cp ^ "_" ^ after_last_dot tyc) cps)
                        in Option.map (fn cp => (inst_s, (cls, tyc, vs', cp, sym))) cp_opt end
                  end
              end
          | _ => NONE)
          stmt_list
      end;

    (** All instance-method constants (suppressed as standalone functions). **)
    val inst_method_syms = map (fn (_, (_, _, _, _, sym)) => sym) inst_methods;
    (** Canonical key for a type constructor at the Rust level. A code_printing-
        mapped type (e.g. nat/int -> BigInt) collapses onto its target name, so
        two HOL types sharing one Rust type get the same key. Rust rejects two
        `impl Trait for BigInt`, so this drives deduplication of reconstructed
        instances; an UNmapped type keys on its own (distinct) name. **)
    fun canon_tyco t =
      (case tyco_syntax t of
          SOME (n, pr) =>
            (("\^E" ^ Pretty.unformatted_string_of
                (pr (fn _ => fn _ => Pretty.str "_") NOBR (replicate n (ITyVar "_"))))
              handle Subscript =>
                error ("DEBUG canon_tyco Subscript: tyco=" ^ t ^ " n=" ^ string_of_int n))
        | NONE => t);
    (** One impl per instance, keyed by a representative method constant; the
        Inst payload carries (class, tyco), the instance vs, and every method. **)
    fun merge_vs inherited vs =
      if length vs <> length inherited then vs
      else map2 (fn (v, sort) => fn (_, inherited_sort) =>
        (v, union (op =) inherited_sort sort)) vs inherited;
    val inst_table_all =
      map (fn seg =>
        let
          val members = filter (fn (s, _) => s = seg) inst_methods
          val (_, (cls, tyc, vs0, _, repr_sym)) = hd members
          (* Different methods of one class instance may use different
             operational dictionaries.  They share the same type-constructor
             parameters, so union their sorts positionally into one impl header. *)
          val vs = fold merge_vs
            (map (fn (_, (_, _, member_vs, _, _)) => member_vs) (tl members)) vs0
          val methods = map (fn (_, (_, _, _, cp, msym)) => (cp, msym)) members
        in (repr_sym, ((cls, tyc), (vs, methods))) end)
        (distinct (op =) (map fst inst_methods));
    (** Deduplicate instances that target the same Rust type: when several HOL
        types map to one Rust type (int & nat -> BigInt), they would each emit
        `impl C for BigInt` (E0119). Group by (class, canon_tyco), keep one
        representative, and union the methods by classparam so the surviving impl
        is as complete as any contributor. Distinct unmapped types are unaffected
        (their canon keys differ). **)
    val inst_table_base =
      let
        fun key (_, ((cls, tyc), _)) = (cls, canon_tyco tyc)
        val keys = distinct (op =) (map key inst_table_all)
      in
        map (fn k =>
          let
            val members = filter (fn e => key e = k) inst_table_all
            val (repr_sym, ((cls, tyc), (vs0, _))) = hd members
            val vs = fold merge_vs
              (map (fn (_, (_, (member_vs, _))) => member_vs) (tl members)) vs0
            val methods =
              distinct (fn ((cp1, _), (cp2, _)) => cp1 = cp2)
                (maps (fn (_, (_, (_, ms))) => ms) members)
          in (repr_sym, ((cls, tyc), (vs, methods))) end)
          keys
      end;

    (** A Rust `impl Derived for T` must satisfy every supertrait implemented by
        the same `T`, including bounds that arise only from executable equations.
        Isabelle sorts do not record such operational bounds: for example an
        equality in a base-class method adds `A: Equal` to `impl Base for T<A>`,
        while the derived method's typescheme may still carry an empty sort.

        Collect every explicit transitive superclass impl for the same canonical
        Rust type and merge its per-parameter sorts into the derived impl header.
        Matching parameters by position follows the shared type-constructor
        application used by all of these instances; unrelated class impls are not
        considered, so their implementation-only bounds do not leak across the
        instance graph. **)
    val inst_table_seed =
      let
        fun direct_supers cls =
          (case Code_Symbol.Graph.get_node program (Type_Class cls) of
            Code_Thingol.Class (_, (classrels, _)) => map snd classrels
          | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        fun superclasses cls =
          let
            fun collect seen [] = seen
              | collect seen (c :: cs) =
                  if member (op =) seen c
                  then collect seen cs
                  else collect (c :: seen) (direct_supers c @ cs)
          in collect [] (direct_supers cls) end;
        fun add_super_bounds (repr_sym, ((cls, tyc), (vs, methods))) =
          let
            val supers = superclasses cls;
            val inherited =
              map_filter (fn (_, ((super, super_tyc), (super_vs, _))) =>
                if member (op =) supers super
                    andalso canon_tyco super_tyc = canon_tyco tyc
                then SOME super_vs
                else NONE)
                inst_table_base;
            val vs' = fold merge_vs inherited vs;
          in
            (repr_sym, ((cls, tyc), (vs', methods)))
          end;
      in map add_super_bounds inst_table_base end;

    (** Rust bounds introduced by one reconstructed impl become requirements of
        every generated body that calls that impl, even when Isabelle's logical
        dictionary does not contain them.  Predicate order is the representative
        case: the executable strict-order method adds `A: Enum` to `Ord for
        Pred<A>`; both `Equal for Pred<A>` and the standalone `contained` helper
        call that Ord impl and must therefore inherit `A: Enum` as well.

        Recover these dependencies from instance-method IConst occurrences.  The
        callee's merged impl variables align with the occurrence's `typargs`; a
        required class is propagated only when the actual argument is one of the
        caller's own type variables.  Repeating to a fixed point also covers a
        short chain of reconstructed method calls without leaking bounds from
        unrelated concrete type arguments. **)
    fun method_bounds_lookup table =
      maps (fn (_, (_, (vs, methods))) =>
        map (fn (_, method_sym) => (method_sym, vs)) methods) table;
    fun add_called_term_bounds method_bounds (IConst {sym, typargs, ...}) bounds =
          (case AList.lookup (op =) method_bounds sym of
            SOME callee_vs =>
              if length callee_vs = length typargs
              then fold (fn ((_, sort), actual_ty) =>
                (case actual_ty of
                  ITyVar v => fold (fn class =>
                    insert (op =) (v, class)) sort
                | _ => I)) (ListPair.zip (callee_vs, typargs)) bounds
              else bounds
          | NONE => bounds)
      | add_called_term_bounds _ (IVar _) bounds = bounds
      | add_called_term_bounds method_bounds (t1 `$ t2) bounds =
          bounds
          |> add_called_term_bounds method_bounds t1
          |> add_called_term_bounds method_bounds t2
      | add_called_term_bounds method_bounds (_ `|=> (body, _)) bounds =
          add_called_term_bounds method_bounds body bounds
      | add_called_term_bounds method_bounds
          (ICase {term, clauses, primitive, ...}) bounds =
          bounds
          |> add_called_term_bounds method_bounds term
          |> add_called_term_bounds method_bounds primitive
          |> fold (fn (pat, body) =>
               add_called_term_bounds method_bounds pat #>
               add_called_term_bounds method_bounds body) clauses;
    fun called_function_bounds method_bounds sym =
      (case Code_Symbol.Graph.get_node program sym of
        Code_Thingol.Fun ((_, raw_eqs), _) =>
          fold (fn ((ts, body), (_, active)) =>
            if active
            then fold (add_called_term_bounds method_bounds) ts #>
              add_called_term_bounds method_bounds body
            else I) raw_eqs []
      | _ => [])
      handle Code_Symbol.Graph.UNDEF _ => [];
    fun merge_named_bounds bounds vs =
      fold (fn (v, class) =>
        map (fn (v', sort) =>
          if v = v' then (v', insert (op =) class sort) else (v', sort)))
        bounds vs;
    fun close_instance_bounds table =
      let
        val method_bounds = method_bounds_lookup table;
        val table' = map (fn (repr_sym, ((class, tyco), (vs, methods))) =>
          let
            val vs' = fold (fn (_, method_sym) =>
              merge_named_bounds
                (called_function_bounds method_bounds method_sym)) methods vs;
          in (repr_sym, ((class, tyco), (vs', methods))) end) table;
      in
        if table' = table then table else close_instance_bounds table'
      end;
    val inst_table = close_instance_bounds inst_table_seed;
    val final_method_bounds = method_bounds_lookup inst_table;
    fun operational_function_vs sym vs =
      merge_named_bounds (called_function_bounds final_method_bounds sym) vs;

    (** Map each reconstructed instance-method constant to (tyco, classparam):
        the concrete type it is implemented for and the trait method it realizes.
        Used at call sites to emit `Tyco::<trait_method>(..)`. Built from the FULL
        (pre-dedup) set so that a call to a dropped duplicate's method still
        resolves -- the call site canonicalizes the tyco (-> BigInt) and lands on
        the surviving impl. **)
    val inst_method_lookup =
      maps (fn (_, ((_, tyc), (_, methods))) =>
        map (fn (cp, msym) => (msym, (tyc, cp))) methods) inst_table_all;
    fun inst_method_info sym = AList.lookup (op =) inst_method_lookup sym;

    (** Constructor-backed instance methods. A class method whose `int`-style
        instance is realised by a `code_datatype` constructor — e.g. `0::int`,
        declared `code_datatype "0::int" Pos Neg` in HOL/Int.thy — reaches the
        backend as a NULLARY `Datatypecons` named like an instance method
        (`<class>_<tyco>_inst.<method>_<tyco>`, e.g. `Int.zero_int_inst.zero_int`),
        NOT as a `Fun`. So `inst_methods` (which scans only `Fun` nodes) misses it
        and no `impl Zero for Int` is reconstructed, even though `Int::zero()` is
        dispatched polymorphically (`of_bool::<Int>`). Detect those constructors so
        the instance impl is emitted with the constructor itself as the method body
        (`fn zero() -> Self { Int::ZeroInta }`) instead of a `panic!` stub.

        These are kept SEPARATE from `inst_method_lookup` on purpose: the symbol is
        a constructor, so its value/pattern sites must keep printing as
        `Int::ZeroInta` (handled by the `is_constr` branch of `print_app_expr`),
        never as a `Tyco::zero()` call. **)
    val constr_inst_data =
      let
        fun after_last_dot s =
          (case List.rev (String.fields (fn c => c = #".") s) of [] => s | x :: _ => x);
        fun before_last_dot s =
          (case List.rev (String.fields (fn c => c = #".") s) of _ :: x2 :: _ => x2 | _ => s);
        fun class_classparams cls =
          (case Code_Symbol.Graph.get_node program (Type_Class cls) of
              Code_Thingol.Class (_, (_, cps)) => cps
            | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        val all_classes =
          distinct (op =) (map_filter (fn ((s, st), _) =>
            case (s, st) of
              (Type_Class c, Code_Thingol.Class _) => SOME c
            | _ => NONE) stmt_list);
        (* A constructor is nullary iff its parent datatype lists it with no
           field types — only such constructors realise a value-typed class
           method like `zero :: 'a`. *)
        fun is_nullary_constr parent const =
          (case Code_Symbol.Graph.get_node program (Type_Constructor parent) of
              Code_Thingol.Datatype (_, cos) =>
                (case AList.lookup (op =) (map (fn ((co, _), tys) => (co, tys)) cos) const of
                    SOME tys => null tys
                  | NONE => false)
            | _ => false)
          handle Code_Symbol.Graph.UNDEF _ => false;
      in
        map_filter (fn ((sym, stmt), _) =>
          case (sym, stmt) of
            (Constant const, Code_Thingol.Datatypecons parent) =>
              if not (is_nullary_constr parent const) then NONE
              else
                let
                  val inst_s = before_last_dot const
                  val hit = find_first (fn cls =>
                    (after_last_dot cls ^ "_" ^ after_last_dot parent ^ "_inst") = inst_s)
                    all_classes
                in
                  case hit of
                    NONE => NONE
                  | SOME cls =>
                      let
                        val cps = class_classparams cls
                        val cp_opt = Option.map fst (find_first (fn (cp, _) =>
                          after_last_dot const = after_last_dot cp ^ "_" ^ after_last_dot parent) cps)
                      in Option.map (fn cp => (cls, parent, cp, sym)) cp_opt end
                end
          | _ => NONE)
          stmt_list
      end;
    (** Map (classparam, tyco) -> the constructor that realises that method, so the
        Inst printer fills the method body with the constructor instead of a stub. **)
    val constr_method_lookup =
      map (fn (_, tyc, cp, sym) => ((cp, tyc), sym)) constr_inst_data;
    fun constr_method_of cp tyc = AList.lookup (op =) constr_method_lookup (cp, tyc);
    (** The (class, tyco) pairs realised by a constructor — emitted as instance
        impls (so the impl exists even when no superclass closure pulls it in) and
        treated as "provided" by the closure pass to avoid a duplicate stub. **)
    val constr_inst_ct = distinct (op =) (map (fn (cls, t, _, _) => (cls, t)) constr_inst_data);

    (** Superclass-closure completion. A reconstructed `impl C for T` obliges T to
        implement every superclass of C too (the trait hierarchy declares those as
        supertrait bounds). Isabelle only code-generates the instances reachable
        from the export root, so some superclass instances are absent — e.g.
        `impl Zero for Int` is missing because Int's zero is the constructor
        `Int::ZeroInta`, so no `zero` method is generated, yet `SemiringBits` &c.
        transitively require `Int: Zero`. Empty marker superclasses are already
        covered by the blanket impl emitted with each trait; the NON-EMPTY ones
        need a stub `impl S for T { fn m(..) { panic!() } }` (the method is
        unreachable, so the panic is dead). Compute those missing (class, tyco)
        pairs here and emit them next to T's datatype declaration. **)
    val closure_inst_data =
      let
        fun class_node c =
          (SOME (Code_Symbol.Graph.get_node program (Type_Class c))
           handle Code_Symbol.Graph.UNDEF _ => NONE)
        fun direct_supers c =
          (case class_node c of SOME (Code_Thingol.Class (_, (classrels, _))) => map snd classrels | _ => [])
        fun class_nonempty c =
          (case class_node c of SOME (Code_Thingol.Class (_, (_, cps))) => not (null cps) | _ => false)
        fun supers_closure c =
          let fun go acc [] = acc
                | go acc (x :: xs) =
                    if member (op =) acc x then go acc xs
                    else go (x :: acc) (direct_supers x @ xs)
          in go [] (direct_supers c) end
        val reconstructed_ct = distinct (op =) (map (fn (_, ((c, t), _)) => (c, t)) inst_table)
        (* A (class, Rust-type) is already provided either by a reconstructed Fun
           instance or by a constructor-backed one; the closure pass must not also
           stub it. Compared on canon_tyco so a mapped type (int/nat -> BigInt) is
           recognised as provided regardless of which HOL type reconstructed it. *)
        val provided_canon =
          distinct (op =)
            (map (fn (c, t) => (c, canon_tyco t)) (reconstructed_ct @ constr_inst_ct))
        fun datatype_vs t =
          (case Code_Symbol.Graph.get_node program (Type_Constructor t) of
              Code_Thingol.Datatype (vns, _) => map (fn v => (v, [])) vns
            | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        val tyco_vs = map (fn (_, ((_, t), (vs, _))) => (t, vs)) inst_table
        fun vs_of_tyco t =
          (case AList.lookup (op =) tyco_vs t of SOME vs => vs | NONE => datatype_vs t)
        val missing =
          maps (fn (c, t) =>
             map_filter (fn s =>
               if class_nonempty s andalso not (member (op =) provided_canon (s, canon_tyco t))
               then SOME (s, t) else NONE)
               (supers_closure c))
             reconstructed_ct
        (* Constructor-backed instances are emitted here too (with the constructor
           filled in as the method body by the Inst printer), so the impl is
           present even when no superclass closure references it. Drop any that a
           Fun instance already reconstructs — that impl's stub pass fills the
           constructor body, and emitting it again would be a duplicate impl. *)
        val all_pairs0 =
          missing
          @ filter_out (fn (c, t) => member (op =) (map (fn (c', t') => (c', canon_tyco t')) reconstructed_ct) (c, canon_tyco t))
              constr_inst_ct
        (* Collapse pairs onto one impl per (class, Rust-type): two HOL types
           mapping to the same Rust type (int & nat -> BigInt) must not both emit a
           superclass stub `impl S for BigInt`. *)
        val all_pairs =
          let val ks = distinct (op =) (map (fn (s, t) => (s, canon_tyco t)) all_pairs0)
          in map (fn k => the (find_first (fn (s, t) => (s, canon_tyco t) = k) all_pairs0)) ks end
      in map (fn (s, t) => (s, t, vs_of_tyco t)) all_pairs end;

    (** Missing superclass implementations for a code_printing-mapped type cannot
        follow a Datas statement: the mapped Rust type is external and its HOL
        Type_Constructor is deliberately not emitted.  Choose one reconstructed
        instance of the same canonical Rust type as the unique output host.  The
        host's Inst statement is later widened to an InstGroup containing both the
        executable impl and these legality-only superclass impls.  Grouping by the
        representative symbol prevents duplicate Rust impls when several missing
        superclasses belong to the same mapped type. **)
    val orphan_closure_hosts =
      let
        val orphan_insts =
          map (fn (cls, t, vs) => ((cls, t), (vs, [])))
            (filter (fn (_, t, _) => is_some (tyco_syntax t)) closure_inst_data);
        val host_syms =
          distinct (op =) (map_filter (fn ((_, t), _) =>
            Option.map (fn (host_sym, _) => host_sym)
              (find_first (fn (_, ((_, host_t), _)) => canon_tyco host_t = canon_tyco t)
                inst_table)) orphan_insts);
        fun hosted_by host_sym =
          let
            val (_, ((_, host_t), _)) =
              the (find_first (fn (sym, _) => sym = host_sym) inst_table);
          in
            filter (fn ((_, t), _) => canon_tyco t = canon_tyco host_t) orphan_insts
          end;
      in map (fn host_sym => (host_sym, hosted_by host_sym)) host_syms end;

    (* build program *)
    val { deresolver, hierarchical_program = rust_program } =
      rust_program_of_program ctxt module_name (Name.make_context reserved_syms)
        identifiers (inst_method_syms, inst_table) operational_function_vs
        closure_inst_data orphan_closure_hosts exports program;


    (** Global lookup functions: query the program graph for type/class info. **)
    (** Look up a symbol's statement in the program graph, returning NoStmt on missing. 
    program: Code_Symbol.Graph of (key: Code_Symbol.T, ord: Code_Thingol.stmt) **)
    fun get_node program sym =         
      (Code_Symbol.Graph.get_node program sym) 
      handle (Code_Symbol.Graph.UNDEF x) => Code_Thingol.NoStmt

    fun lookup_dependent_types_h program sym dpdncs =
      let 
        fun dest_itype (ITyVar vn) = [vn]
          | dest_itype (v `%% vns) = v::(List.concat(map dest_itype vns))
        fun dest_types (Code_Thingol.Datatype (_(*vns*), cos)) = 
          cos  
          |> map (fn ((_, _), ityps) => ityps)
          |> List.concat
          |> map dest_itype
          |> List.concat
          |> distinct (op =)
          | dest_types _ = [] (*raise Fail ("dest_types: "^ print_debug_info_thingol_stmt x)*)
        val drct_dpdncs = dest_types (get_node program sym)
        val snd_dpdncs = drct_dpdncs@dpdncs 
          |> map (fn t => (Type_Constructor t)) 
          |> map (get_node program)
          |> map dest_types
          |> List.concat
          |> (fn l => l@drct_dpdncs@dpdncs)
          |> distinct (op =)
      in
        if (List.length dpdncs) = (List.length (snd_dpdncs))
        then dpdncs
        else lookup_dependent_types_h program sym snd_dpdncs
      end;
    fun lookup_dependent_types program sym = lookup_dependent_types_h program sym [];
    (** Names of all type constructors / type variables mentioned in an itype,
        descending through type arguments (so e.g. tree is found in `tree list`). **)
    fun type_names (ITyVar vn) = [vn]
      | type_names (tyco `%% tys) = tyco :: maps type_names tys;
    (** Whether type aty can transitively reach datatype co: either co is mentioned
        syntactically (incl. inside a type argument) or it lies in the recursive
        datatype-definition closure of some type aty mentions. Boxing on this
        predicate is conservative -- over-boxing only adds an indirection, whereas
        under-boxing yields an infinite-size Rust type (E0072). **)
    fun type_reaches co aty =
      let
        val hs = distinct (op =) (type_names aty)
        val reach = hs @ maps (lookup_dependent_types program o Type_Constructor) hs
      in member (op =) reach co end;
    (** Which fields of a data constructor need Box<>, decided on the
        constructor's POLYMORPHIC definition (looked up via the parent datatype),
        NOT any instantiated call-site domain: a generic field such as List's
        `Cons` head is a bare type variable and must never be boxed. The same
        per-field bool list drives both the enum declaration (type-level Box<...>)
        and construction/pattern printing (term-level Box::new / box), keeping the
        two consistent. Precomputed into box_table so the printer never reruns the
        type_reaches fixpoint. **)
    fun box_list_of_constr sym =
      (case get_node program sym of
        Code_Thingol.Datatypecons parent =>
          (case get_node program (Type_Constructor parent) of
            Code_Thingol.Datatype (_, cos) =>
              (case AList.lookup (op =) (map (fn ((co, _), tys) => (co, tys)) cos)
                     (case sym of Constant c => c | _ => "") of
                SOME poly_tys => map (type_reaches parent) poly_tys
              | NONE => [])
          | _ => [])
      | _ => []);
    val box_table =
      let
        val tab = fold (fn ((sym, stmt), _) =>
          (case (sym, stmt) of
            (Constant _, Code_Thingol.Datatypecons _) =>
              Code_Symbol.Table.update (sym, box_list_of_constr sym)
          | _ => I)) stmt_list Code_Symbol.Table.empty
      in fn sym => the_default [] (Code_Symbol.Table.lookup tab sym) end;
    (** Phantom type parameters of a datatype: declared generic params (vs) that
        appear in NO constructor field type. Rust rejects an unused generic
        (E0392), so each is materialised as a PhantomData<Ti> marker field. Order
        follows vs so the enum declaration and the per-constructor markers agree.
        Precomputed into phantom_table, keyed by the datatype's Type_Constructor. **)
    fun phantom_vars_of_datatype (vs, cos) =
      let
        val used = cos |> maps (fn (_, tys) => maps type_names tys) |> distinct (op =)
      in filter_out (member (op =) used) vs end;
    val phantom_table =
      let
        val tab = fold (fn ((sym, stmt), _) =>
          (case (sym, stmt) of
            (Type_Constructor _, Code_Thingol.Datatype (vs, cos)) =>
              Code_Symbol.Table.update (sym, phantom_vars_of_datatype (vs, cos))
          | _ => I)) stmt_list Code_Symbol.Table.empty
      in fn sym => the_default [] (Code_Symbol.Table.lookup tab sym) end;
    (** Look up whether a constant is a data constructor; returns SOME parent_tyco or NONE. **)
    fun lookup_constant_typeco_gen program sym =
      let
        val stmt = get_node program sym
      in
        (case stmt
        of Code_Thingol.Datatypecons c => SOME c
          | _ => NONE)
      end handle Code_Symbol.Graph.UNDEF _ => NONE;
    val lookup_constant_typeco = lookup_constant_typeco_gen program;
    (** Polymorphic constructor fields together with their result datatype
        parameters.  The term-level IConst contains only instantiated dom/range;
        retaining this declaration template lets the printer propagate a caller's
        expected higher-order shape through native tuple and datatype syntax. **)
    fun lookup_constructor_fields sym =
      (case lookup_constant_typeco sym of
        SOME parent =>
          (case get_node program (Type_Constructor parent) of
            Code_Thingol.Datatype (vs, cos) =>
              Option.map (fn fields => (parent, vs, fields))
                (AList.lookup (op =)
                  (map (fn ((co, _), fields) => (Constant co, fields)) cos) sym)
          | _ => NONE)
      | NONE => NONE);
    fun is_single_constr sym =
      ((case lookup_constant_typeco sym of
        SOME parent =>
          (case get_node program (Type_Constructor parent) of
            Code_Thingol.Datatype (_, cos) => length cos = 1
          | _ => false)
      | NONE => false)
      handle Code_Symbol.Graph.UNDEF _ => false);
    (** Look up whether a constant is a function; returns SOME function signiture or NONE. **)    
    fun lookup_constant_fun_gen program sym = 
      let
        val stmt = get_node program sym
      in
        (case stmt 
        of Code_Thingol.Fun f => SOME f
          | _ => NONE)
      end; 
    val lookup_constant_fun = lookup_constant_fun_gen program;
    (** Look up which class a class parameter (method) belongs to.
        Returns NONE for symbols that are not class parameters. **)
    fun lookup_method_class_gen program sym =
      (case get_node program sym
        of Code_Thingol.Classparam c => SOME c
         | _ => NONE)
    val lookup_method_class = lookup_method_class_gen program
    (** A class's own type variable and its full classparam list
        [(classparam_const, method_itype), ..]. NONE for non-class symbols.
        Lets the Inst printer complete an instance impl with stub bodies for
        methods that the instance does not code-generate (e.g. word's unused
        mask/set_bit/.. in semiring_bit_operations), which Rust would otherwise
        reject as an incomplete impl (E0046). **)
    fun lookup_class_methods_gen program class =
      (case get_node program (Type_Class class)
        of Code_Thingol.Class (v, (_, cps)) => SOME (v, cps)
         | _ => NONE)
    val lookup_class_methods = lookup_class_methods_gen program
      
    (** Compute module-level import dependencies.
        Module and item paths must come from the namespace deresolver so
        code_identifier remappings such as Nat/Power -> Arith are respected. **)
    val generated_top_modules =
      Code_Namespace.print_hierarchical {
        print_module = fn _ => fn base => fn _ => fn _ => base,
        print_stmt = fn _ => fn _ => "",
        lift_markup = K I } rust_program
      |> filter (fn s => s <> "")
      |> distinct (op =)
    val raw_modules = generated_top_modules

    fun fields s = String.fields (fn c => c = #".") s
    fun after_last_dot s = (case List.rev (fields s) of x :: _ => x | [] => s)
    fun module_of_qualified_name s =
      (case List.rev (fields s) of
        _ :: rev_module => String.concatWith "." (List.rev rev_module)
      | [] => "")
    fun crate_path qual = "crate::" ^ String.concatWith "::" (fields qual)
    val generated_modules =
      fold (fn ((sym, _), _) => fn modules =>
        (case try (deresolver []) sym of
          SOME qual =>
            let val module = module_of_qualified_name qual
            in if module = "" then modules else insert (op =) module modules end
        | NONE => modules)) stmt_list []
    fun is_generated_module module =
      List.exists (fn module' => module' = module) generated_modules

    val module_local_bases =
      fold (fn ((sym, _), _) =>
        (case try (deresolver []) sym of
          SOME qual =>
            let
              val module = module_of_qualified_name qual
              val base = after_last_dot qual
            in
              if is_generated_module module
              then AList.map_default (op =) (module, []) (insert (op =) base)
              else I
            end
        | NONE => I)) stmt_list []

    fun import_syms_for_dep sym =
      (case inst_method_info sym of
        (* A call dispatched as `Tyco::method()` through a reconstructed instance
           needs the TRAIT in scope (Rust resolves the inherent/trait method only
           if the trait is imported), plus the receiver type. The dependency is
           recorded on the instance-method constant (which is itself suppressed),
           so neither would be imported by the constant alone. *)
        SOME (tyco, cp) =>
          (case lookup_method_class (Constant cp) of SOME c => [Type_Class c] | NONE => [])
          @ [Type_Constructor tyco]
      | NONE =>
          (case get_node program sym of
            Code_Thingol.Datatypecons parent => [Type_Constructor parent]
          | Code_Thingol.Classparam class => [Type_Class class]
          | _ => [sym]))

    fun emitted_import_symbol sym =
      (case (sym, get_node program sym) of
        (Constant const, stmt as Code_Thingol.Fun _) =>
          is_none (const_syntax const) andalso
          not (Code_Thingol.is_case stmt) andalso
          not (member (op =) inst_method_syms sym)
      | (Type_Constructor tyco, Code_Thingol.Datatype _) => is_none (tyco_syntax tyco)
      | (Type_Class _, Code_Thingol.Class _) => true
      | _ => false)

    fun import_candidate source_module sym =
      (* Guard on emitted_import_symbol FIRST: a code_printing-mapped symbol (e.g.
         Type_Constructor nat/int -> BigInt) has no program node, so calling
         deresolver on it would raise "Unknown statement name". *)
      if not (emitted_import_symbol sym) then NONE
      else
        let
          val qual = deresolver [] sym
          val segs = fields qual
        in
          (case segs of
            [_] => NONE
          | _ =>
              let
                val dep_module = module_of_qualified_name qual
                val base = after_last_dot qual
              in
                if dep_module <> source_module andalso is_generated_module dep_module
                then SOME (sym, qual, base, crate_path qual)
                else NONE
              end)
        end

    fun same_candidate ((_, qual1, _, _), (_, qual2, _, _)) = qual1 = qual2

    val module_import_candidates =
      let
        fun add_candidate module cand =
          AList.map_default (op =) (module, []) (insert same_candidate cand)
        fun add_sym_import source_module dep imports =
          (case import_candidate source_module dep of
            SOME cand => add_candidate source_module cand imports
          | NONE => imports)
        fun add_imports_for_sym (sym, children) imports =
          (case try (deresolver []) sym of
            SOME qual =>
              let
                val source_module = module_of_qualified_name qual
                val deps = maps import_syms_for_dep children
              in
                if is_generated_module source_module
                then fold (add_sym_import source_module) deps imports
                else imports
              end
          | NONE => imports)
      in
        fold add_imports_for_sym sym_dpdnc_list []
      end

    fun candidate_sym (sym, _, _, _) = sym
    fun candidate_base (_, _, base, _) = base
    fun candidate_crate_path (_, _, _, path) = path

    fun local_base module base =
      member (op =) (these (AList.lookup (op =) module_local_bases module)) base

    fun candidate_is_ambiguous cands base =
      let
        val paths =
          cands
          |> filter (fn cand => candidate_base cand = base)
          |> map candidate_crate_path
          |> distinct (op =)
      in length paths > 1 end

    fun importable_candidate cands module cand =
      not (candidate_is_ambiguous cands (candidate_base cand)) andalso
      not (local_base module (candidate_base cand))

    val module_symbol_imports =
      module_import_candidates
      |> map (fn (module, cands) =>
          let
            val safe_cands = filter (importable_candidate cands module) cands
            val paths = map candidate_crate_path safe_cands |> sort_distinct string_ord
            val syms = map candidate_sym safe_cands |> distinct (op =)
          in (module, (paths, syms)) end)

    fun sym_uses_short_path module sym =
      (case AList.lookup (op =) module_symbol_imports module of
        SOME (_, syms) => member (op =) syms sym
      | NONE => false)

    (** Map a Code_Namespace resolved name to a Rust path. The deresolver returns
        a dot-separated name relative to the current module. Local names stay
        bare. Cross-module names use an imported short name only when that base
        name is unique in this module; otherwise they stay fully crate-qualified. **)
    fun modify_deresolver module local_deresolver sym =
      (case fields (local_deresolver sym) of
        [base] => base
      | _ =>
          if sym_uses_short_path module sym
          then after_last_dot (deresolver [] sym)
          else crate_path (deresolver [] sym))

    (** Print a single statement within its module context. **)
    fun print_stmt prefix_fragments (sym, (export, stmt)) =
      let
        val current_module = String.concatWith "." prefix_fragments
        fun is_constr_safe sym =
          (Code_Thingol.is_constr program sym
            handle Code_Symbol.Graph.UNDEF _ => false)
        val _ = tracing ("[Thingol] "
          ^ Code_Debug_Info.print_debug_info_sym sym ^ ": "
          ^ Code_Debug_Info.print_debug_info_thingol_stmt (get_node program sym))
        val r = Exn.result (fn () =>
          (print_rust_stmt
            tyco_syntax const_syntax (make_vars reserved_syms)
            is_constr_safe (modify_deresolver current_module (deresolver prefix_fragments))
            box_table phantom_table
            lookup_constant_typeco lookup_constructor_fields is_single_constr lookup_constant_fun
            lookup_method_class inst_method_info lookup_class_methods constr_method_of)
            export stmt
          |> apfst (fn decl => if Code_Namespace.not_private export then SOME decl else NONE)) ()
        val _ = (case r of
            Exn.Exn e => warning ("RUST-STMT-CRASH at sym: " ^ Code_Debug_Info.print_debug_info_sym sym
              ^ "\n  exn: " ^ General.exnMessage e
              ^ "\n  stmt: " ^ Code_Debug_Info.print_debug_info_thingol_stmt (get_node program sym))
          | _ => ())
      in
        Exn.release r
      end;

    (** Print a module: gather declarations, resolve imports, and wrap in module body. **)
    fun print_module prefix_fragments base _ xs =
      let
        val (raw_decls, body) = split_list xs;
        val decls = maps these raw_decls
        val current_module = String.concatWith "." prefix_fragments
        val crate_uses =
          (case AList.lookup (op =) module_symbol_imports current_module of
            SOME (paths, _) => paths
            | NONE => [])
        val module_body = print_rust_module base decls crate_uses rust_includes body
        val rendered =
          if length prefix_fragments = 1 then module_body
          else rust_block (str ("pub mod " ^ base)) [module_body]
      in (SOME [str base], rendered) end;

    (** Assemble final output: Cargo.toml + lib.rs + per-module .rs files.
        Unused modules get empty placeholder files to pass compilation. **)
    val ps = Code_Namespace.print_hierarchical {
        print_module = print_module, print_stmt = print_stmt,
        lift_markup = K I } rust_program;
    val modules = map fst ps
      |> map (fn (SOME [x]) => (Pretty.string_of x))
    val unused_modules = subtract (op =) modules raw_modules
    val srcs = ListPair.zip
      (map (fn x => ["src", x^rust_extension]) modules,
      map snd includes @ map snd ps)
    val empty_mods = map (fn x => (pair
        (["src", x^rust_extension])
        (str "/*Empty module, added to pass compilition*/")))
      unused_modules
    val toml = pair
      (["Cargo.toml"])
      (Pretty.chunks2 ([
          Pretty.chunks ([str "[package]",
                str ("name = "^rust_module),
                str ("version = "^rust_version),
                str ("edition = "^rust_edition)]),
          Pretty.chunks ([str "[dependencies]", str rust_dependencies]),
          Pretty.chunks ([str "[lints.rust]", str rust_lints])
      ]))
	    val lib = pair
	      (["src", "lib.rs"])
	      (Pretty.chunks([
	        str (fold (fn s => (fn acc => ("pub mod "^s^";\n")^acc)) modules "" )
	      ]))
  in
    (Code_Target.Hierarchy (toml :: lib :: srcs @ empty_mods),
    try (deresolver []))
  end;

(** Wrapper: parse Isar arguments and invoke serialize_rust with defaults. **)
val serializer_rust : Code_Target.serializer =
  Code_Target.parse_args (Scan.succeed ()) #> K (serialize_rust "" "" "" "" "" [] print_rust_module print_rust_stmt ".rs");


(** Isar setup **)

(** Custom type syntax for "fun" type constructor:
    renders as "Rc<dyn Fn(A, B) -> C>" in Rust. **)
fun fn_trait_impl_syntax print_typ fxy [ty1, ty2] =
  let
    val ts = extract_typ print_typ ("fun"`%%[ty1, ty2])
    val ret = List.last ts
    val params = List.take (ts, ((List.length ts) - 1))
  in
    rc_dyn_fn params ret
  end;

(** Register Rust as a code generation target in Isabelle.
    Sets up the serializer, Cargo-based checking, literal syntax, fun type
    printing, and reserved words. **)
val _ = Theory.setup
  (Code_Target.add_language
    (target, {serializer = serializer_rust, literals = literals_rust,
      (* `export_code ... checking Rust` exports the generated hierarchy as a
         complete Cargo crate directly into Isabelle's temporary check directory
         (Cargo.toml plus src/*.rs).  The check command therefore only has to
         run Cargo in that directory.  The Rust backend emits `box_patterns` and
         large HOL stress exports routinely contain unused support items, so the
         same environment used by the existing stage1 Cargo tests is applied. *)
      check = {env_var = "ISABELLE_CARGO",
        make_destination = I,
        make_command = fn _ =>
          "RUSTC_BOOTSTRAP=1 RUSTFLAGS=\"-Awarnings\" \"$ISABELLE_CARGO\" build"},
      evaluation_args = []})
  #> Code_Target.set_printings (Type_Constructor ("fun",
    [(target, SOME (2, fn_trait_impl_syntax))]))
  #> fold (Code_Target.add_reserved target) [
    "Self", "abstract", "alignof", "and", "any", "as", "assert", "become", 
    "begin", "box", "break","case", "chan", "class", "const", "constraint", 
    "continue", "crate", "default", "defer", "do", "done", "downto", 
    "else", "end", "enum", "exception", "extern", "extern crate", "external", 
    "fallthrough", "false", "final", "fn", "for", "fun", "func", "function", "functor", 
    "go", "goto", "if", "if let", "impl", "import", "in", "include", "inherit", 
    "initializer", "interface", "lazy", "let", "loop", "macro", "map", "match", "method", 
    "mod", "module", "move", "mut", "mutable", "new", "object", "of", "offsetof", "open", 
    "or", "override", "package", "priv", "private", "proc", "pub", "pure", "range", 
    "rec", "ref", "return", "select", "self", "sig", "sizeof", "static", "struct", 
    "super", "switch", "then", "to", "trait", "true", "try", "type", "typeof", "unsafe",
    "unsized", "use", "val", "var", "virtual", "when", "where", "while", "with", "yield"]
  #> fold (Code_Target.add_reserved target) ["failwith", "Z"]);

end; (*struct*)
