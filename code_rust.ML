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
  | Inst of (class * string) * ((vname * sort) list * (string * Code_Symbol.T) list);

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
    fun combine (x1::x2::_::l) = Pretty.block [x1, x2, str" "] :: combine l   
      | combine [x] = [x]
      | combine [] = []
  in
    combine (Pretty.commas prts)
  end

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
  lookup_constant_typeco lookup_constant_fun
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
    fun print_tyco_expr (sym, tys) = print_tyco_expr_gen (sym, tys);
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
    (** Main term printer. Handles all iterm constructors:
        IConst (constants/constructors), IVar (variables), `$ (application),
        `|=> (lambda/pattern abstraction), ICase (case/let/match).
        The triple (need_box, box_prcs, clone_prcs) controls Box/clone wrapping:
          need_box: whether to wrap the result in Box
          box_prcs: box wrapping function (box_new for exprs, box_pattern for patterns)
          clone_prcs: clone wrapping function (clone for exprs, I for patterns) **)
    fun print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy (IConst const) =
          let
            fun print_const (IConst const) =
              print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars fxy (const, [])
          in
            print_term_with_cons_and_box (need_box, box_prcs) print_const (IConst const) 
          end
      | print_term_gen _ _ _ _ _ (IVar NONE) =
          str "_"
      | print_term_gen _ (need_box, box_prcs, clone_prcs) _ vars _ (t as (IVar (SOME v))) =
          if need_box
          then box_prcs (clone_prcs (str (lookup_var vars v)))
          else clone_prcs (str (lookup_var vars v))
      | print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy (t as t1 `$ t2)=
          let                 
            fun print_app_term (t as t1 `$ t2) =
              (case Code_Thingol.unfold_const_app t
              of SOME app => (*function or typeco*)
                print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars fxy app
              | NONE => (*closure*)
                let
                  val (t', ts') = Code_Thingol.unfold_app t
                  val params = map (print_term_app is_pseudo_fun some_thm vars NOBR) ts'
                in
                  (* The callee is a function value of type Rc<dyn Fn(..)>, which
                     is not directly callable (unlike Box, Rc has no Fn impl).
                     Deref to the `dyn Fn` place, emitting the form  ( * f )(args). *)
                  Pretty.block(
                    str "(*"
                    :: print_term_decl is_pseudo_fun some_thm vars NOBR t'
                    :: str ")("
                    :: commas_append params
                    @ [str ")"]
                  )
                end)
          in
            print_term_with_cons_and_box (need_box, box_prcs) print_app_term t
          end
      | print_term_gen is_pseudo_fun _ some_thm vars _ (t as _ `|=> _) =
          print_lambda is_pseudo_fun some_thm vars t
      | print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy (t as (ICase case_expr)) =
          case Code_Thingol.unfold_const_app (#primitive case_expr)
            of SOME (app as ({ sym = Constant const, ... }, _)) =>
                  if is_none (const_syntax const)
                  then print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy case_expr
                  else print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars fxy app
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
    and print_term_with_cons_and_box (need_box, box_prcs) print_term t = 
      let
        fun lookup_typeco t =
          (case (Code_Thingol.unfold_const_app t)
            of (SOME ((const as {sym as (Constant c), ...}), _))
              => lookup_constant_typeco sym
            | _ => NONE)
        (* The `Enum::` prefix is the (possibly crate-qualified) name of the parent
           datatype, taken straight from the deresolver so it matches the enum
           declaration and resolves across modules without a glob import. *)
        fun print_cons (SOME parent) = deresolve (Type_Constructor parent)
          | print_cons NONE = ""
        (* A constructor used as a first-class value (no args, non-empty domain)
           is eta-expanded into a closure by print_app_expr, so it must NOT get
           the `Tyco::` prefix -- that belongs only on an actual constructor
           reference. *)
        val is_eta_constr =
          (case Code_Thingol.unfold_const_app t
            of SOME (({ dom, ... }), []) => not (null dom)
            | _ => false)
        val typeco_s = if is_eta_constr then "" else print_cons (lookup_typeco t)
        val term = print_term t
        val term_with_cons =
          if typeco_s = "" then term
          else Pretty.block [str (typeco_s ^ "::"), term]
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
    and print_app_expr is_pseudo_fun (box_prcs, clone_prcs)
       some_thm vars (app as ((const as { sym, dicts, dom, range, ... }), ts)) =
        if is_constr sym then
          let
            val wanted = length dom
            val need_box_list = box_table sym
            (* One PhantomData marker per phantom param of the parent datatype,
               appended after the real args. Valid as both an expression (unit
               struct) and an irrefutable pattern, so no expr/pattern split here. *)
            val phantom_count =
              (case lookup_constant_typeco sym of
                SOME parent => length (phantom_table (Type_Constructor parent))
              | NONE => 0)
            val phantom_args = List.tabulate (phantom_count, fn _ => str "PhantomData")
          in
            if wanted = 0
            then
              if phantom_count = 0
              then [(str o deresolve_base) sym]
              else [(str o deresolve_base) sym, enum "," "(" ")" phantom_args]
            else if length ts = wanted
            then
              [(str o deresolve_base) sym,
               enum "," "(" ")"
                 (map
                   (fn (t, need_box) =>
                     print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars NOBR t)
                   (ListPair.zip (ts, need_box_list))
                  @ phantom_args)]
            else 
              let 
                val saturated_t = Code_Thingol.saturated_application wanted app
              in
                [print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR saturated_t]
              end 
          end
        else if is_pseudo_fun sym
          then (str o deresolve) sym @@ str "()"
        else
          let 
            val wanted_app = length dom
            (** Mirror the eta-expansion in binding_of_stmt: a single equation with
                empty LHS (e.g., [size_list = gen_length zero_nat]) is eta-expanded
                to one argument before being emitted as a Rust function. **)
            val wanted_fn = case lookup_constant_fun sym
              of SOME (((vs, ty), raw_eqs), _) =>
                   let
                     val eqs = filter (snd o snd) raw_eqs
                   in
                     case eqs
                      of [] => wanted_app
                       | [(([], _), _)] =>
                           if null (filter_out (null o snd) vs)
                              andalso (not o null o fst o Code_Thingol.unfold_fun) ty
                           then 1
                           else 0
                       | _ => length (hd (map (fst o fst) eqs))
                   end
              | NONE => wanted_app
            fun print_generic_prefix_typ ty =
              (print_typ NOBR (case ty of (tyco`%%_) => tyco`%%[] | ty => ty))
            val prefix_target_ty = if List.null dom then range else List.hd dom
            (* A type-variable receiver is generic dispatch (`A::method`). *)
            val is_tyvar_receiver =
              (case prefix_target_ty of (ITyVar _) => true | _ => false)
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
            (* Decide the printed callee and any `Receiver::` prefix. *)
            val (generic_prefixs, funcname) =
              (case inst_method_info sym of
                  SOME (tyco_s, cp_s) =>
                    ([Pretty.block [str (deresolve (Type_Constructor tyco_s)), str "::"]],
                     str (deresolve_base (Constant cp_s)))
                | NONE =>
                    if is_some (lookup_method_class sym)
                    then (case classparam_dispatch_var of
                            SOME v =>
                              ([Pretty.block [str (to_upper v), str "::"]],
                               (str o deresolve_base) sym)
                          | NONE =>
                              if is_tyvar_receiver
                              then ([Pretty.block [print_generic_prefix_typ prefix_target_ty, str "::"]],
                                    (str o deresolve_base) sym)
                              else ([], (str o deresolve) sym))
                    else ([], (str o deresolve) sym))
          in
            if length ts = wanted_app
            then
              let
                val (ts1, ts2) = chop wanted_fn ts
                val call1 =
                  generic_prefixs
                  @ funcname
                  :: the_list turbofish
                   @ [enum "," "(" ")"
                       (map
                         (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR)
                       ts1)]
              in
                if List.null ts2
                then [Pretty.block call1]
                else
                  (* funcname(ts1) yields an Rc<dyn Fn(..)> result; deref it to
                     call the remaining argument group, emitting ( * funcname(ts1) )(ts2). *)
                  [Pretty.block (
                    str "(*"
                    :: Pretty.block call1
                    :: str ")"
                    :: [enum "," "(" ")"
                          (map
                            (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR)
                          ts2)]
                  )]
              end
            else
              let 
                val saturated_t = Code_Thingol.saturated_application wanted_app app
              in
                [print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR saturated_t]
              end 
          end
    (** Print an application, applying registered const_syntax if any and
        otherwise falling back to print_app_expr. print_app prints arguments
        without Box/clone; print_app_with_clone threads the (box_prcs, clone_prcs)
        wrappers through both ordinary calls and custom-syntax subterms. **)
    and print_app is_pseudo_fun some_thm vars =
      gen_print_app (print_app_expr is_pseudo_fun (I, I))
      (print_term_decl is_pseudo_fun) const_syntax some_thm vars
    and print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars =
      gen_print_app (print_app_expr is_pseudo_fun (box_prcs, clone_prcs))
      (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs)) const_syntax some_thm vars
    (** Bind a clause pattern, introducing its variables (printed as a pattern). **)
    and print_bind is_pseudo_fun = gen_print_bind (print_term_pattern is_pseudo_fun)
    (** Print a case expression. Three cases:
        - Empty clauses: generates panic
        - Single clause: emitted as let-binding block
        - Multiple clauses: emitted as match block **)
    and print_case _ _ _ _ _ { clauses = [], ... } =
          (concat o map str) ["panic!(\"empty case\")", "\"empty case\""]
        (*let bind*)
      | print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars fxy (case_expr as { clauses = [_], ... }) =
          let
            val (binds, body) = Code_Thingol.unfold_let (ICase case_expr);
            fun print_let ((pat, _), t) vars =
              vars
              |> print_bind is_pseudo_fun some_thm NOBR pat
              |>> (fn p => Pretty.block
                  [str "let ", p, str " = ", 
                  print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars NOBR t, str ";"])
            val (ps, vars') = fold_map print_let binds vars;
          in
            Pretty.block_enclose (str "{", str "}")
            (ps @ [print_term_app is_pseudo_fun some_thm vars' NOBR body])
          end     
        (*match block*)     
      | print_case is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars _ (icase as { term = t, typ = _, clauses = clauses, ... }) =
          let
            fun print_select (pat, body) =
              let
                val (p, vars') = print_bind is_pseudo_fun some_thm NOBR pat vars;
              in 
                Pretty.block (
                  p 
                  :: str " => "
                  :: [(print_term_app is_pseudo_fun some_thm vars' NOBR body)]
                )
              end;
          in
            Pretty.block_enclose(
              Pretty.block(
                [str "match ",
                print_term_app is_pseudo_fun some_thm vars NOBR t,
                str " {"]
              ),
              str "}"
            )
            (* HOL functions may be partial (e.g. `nth [] n` has no equation), so
               the clauses need not cover every constructor; Rust requires total
               matches. Add a catch-all that panics on the undefined inputs. On a
               match that is already exhaustive this arm is unreachable — a warning
               (suppressed), not an error. *)
            (commas_append (map print_select clauses
              @ [str "_ => panic!(\"non-exhaustive match\")"]))
          end
    (** Print a `move` closure with explicit capture-by-clone.
        For each outer variable v that occurs free in the body 
        we emit `let v_cap = v.clone();` before the closure
        and rewrite the in-body occurrences to v_cap.
        Closure parameter names (collected via add_varnames on each bind
        pattern) are excluded from the capture set. **)
    and print_lambda is_pseudo_fun some_thm vars t =
      let
        val (binds, t') = Code_Thingol.unfold_pat_abs t;
        val (outer_namemap, outer_namectxt) = vars;
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
        val vars_capped = (outer_namemap', outer_namectxt');
        val (ps, vars') =
          fold_map (print_bind is_pseudo_fun some_thm BR o fst) binds vars_capped;
        val typs = map ((print_typ NOBR) o snd) binds;
        (* Wrap in Rc::new so the closure value has the cloneable trait-object
           type Rc<dyn Fn(..)>. The unsizing coercion Rc<{anon}> -> Rc<dyn Fn>
           happens at the enclosing coercion site (function return, constructor
           argument, typed let), so no `as`/annotation is emitted here. *)
        val closure_pretty =
          Pretty.block_enclose (
            Pretty.block (
              str "Rc::new(move |"
              :: commas_append
                (map (fn (p1, p2) => Pretty.block [p1, str ": ", p2])
                  (ListPair.zip (ps, typs)))
              @ [str "| {"]
            ),
            str "})"
          )
          ([print_term_gen is_pseudo_fun (false, box_new, clone) some_thm vars' NOBR t'])
      in
        if null captured_vars then closure_pretty
        else
          let
            val cap_lets =
              map2
                (fn v => fn vcap =>
                  str ("let " ^ vcap ^ " = " ^ (lookup_var vars v) ^ ".clone();"))
                captured_vars cap_names
          in
            Pretty.block_enclose (str "{", str "}")
              (cap_lets @ [closure_pretty])
          end
      end;          
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
              else concat [
                str (deresolve_const co),
                Pretty.block [str "(", enum "," "" "" phantom_fields, str ")"]
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
              concat [
                str (deresolve_const co),
                Pretty.block(
                  [
                  str "(",
                  enum "," "" "" (data_fields @ phantom_fields),
                  str")"]
                )
              ]
            end;
      in
        Pretty.block_enclose (
          Pretty.chunks([
            str "#[derive(Clone)]",
            Pretty.block (
              [str definer,
              Pretty.brk 1,
              print_tyco_expr (Type_Constructor tyco, map ITyVar vs),
              str " { "]
            )
          ]),         
          str "}"          
        )
        (commas_append (map print_co cos))
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
                     commas_append ((print_vs_traits vs) @ other_traits)
                  end
              in
                pair
                (if List.null generic_params
                then str ""
                else enum "," "<" ">" (map str generic_params))
                (if List.null generic_params
                then str ""
                else
                  Pretty.block_enclose (str "where",str "")
                  (print_traits vs generic_params))
              end;
            (* impl methods carry no generics/where-clause of their own; the bounds
               live on the surrounding impl header (printed by the Inst stmt). *)
            val (generics, traits) =
              if is_impl then (str "", str "")
              else print_generics_and_traits vs ty;
            (** Print a single equation as a match arm: "pattern => expr".
                If is_degenerated (single clause), prints just the expression body. **)
            fun print_eqn is_degenerated ((ts, t), (some_thm, _)) =
              let
                val vars = reserved
                  |> intro_base_names_for (is_none o const_syntax)
                      deresolve (t :: ts)
                  |> intro_vars (build (fold Code_Thingol.add_varnames ts));
                val print_pattern_term = (print_term_pattern is_pseudo_fun some_thm vars NOBR)
                val print_expr_term = (print_term_app is_pseudo_fun some_thm vars NOBR)
              in 
                if is_degenerated (*only 1 pattern clause in eqs*)
                then print_expr_term t 
                else Pretty.block [
                to_tuple ts (
                  Pretty.block(commas_append (map print_pattern_term ts))),
                str " => ",
                print_expr_term t 
                ] 
              end;
            (** Print the function signature and body:
                generates dummy parameter names, type annotations, return type,
                and dispatches to direct expr / single match / multi match body. **)
            fun print_eqns (vs_ty as (vs, ty)) is_pseudo eqs =
                  let
                    val vars = reserved
                          |> intro_base_names_for (is_none o const_syntax)
                              deresolve (map (snd o fst) eqs)
                    val dummy_parms = (map str o aux_params vars o map (fst o fst)) eqs;
                    val typs = extract_typ print_typ ty
                    val param_typs = List.take (typs, (List.length dummy_parms))
                    val ret_typs = List.drop (typs, (List.length dummy_parms))
                    val ret_typ = (case ret_typs
                      of [] => str "()"
                      | [t] => t 
                      | ts => (*Fn Trait*)
                        let
                          val ret = List.last ts
                          val params = List.take (ts, ((List.length ts) - 1))
                        in
                          rc_dyn_fn params ret
                        end)
                    val dummy_parms_with_typs = ListPair.zip (dummy_parms, param_typs)
                      |> map (fn (prt1, prt2) => Pretty.block ([prt1, str ": ", prt2]))
                    fun is_var_pattern (IVar _) = true
                      | is_var_pattern _ = false
                    fun is_const_expr ts t = 
                      let
                        fun unfold_term t = (case t
                          of (_`$_) => (snd o Code_Thingol.unfold_app) t 
                          | (_`|=>(t', _)) => unfold_term t'
                          | (IVar _) => [t]
                          | _ => []) 
                        val pattern_terms = List.concat (map unfold_term ts)
                        val expr_terms = unfold_term t
                      in
                        not (fold (fn t => fn acc => (List.exists (fn t' => t' = t) pattern_terms) orelse acc) expr_terms false)
                      end
                  in
                    Pretty.block_enclose(
                      Pretty.block (
                        (str "("
                        :: Pretty.commas dummy_parms_with_typs)
                        @ str ") -> "
                        :: ret_typ
                        :: Pretty.fbrk
                        :: traits
                        :: [str " {"]
                      ),
                      str "}"
                    )
                    ([(case eqs 
                    of [eq as ((ts, t), _)] =>
                    if List.all is_var_pattern ts andalso is_const_expr ts t
                    then (print_eqn true eq)
                    else Pretty.block (
                        str "match "
                        :: to_tuple dummy_parms ((Pretty.block o commas) dummy_parms)
                        :: str "{"
                        :: print_eqn false eq
                        (* catch-all for a partial HOL function (refutable single
                           clause that need not cover every input); see the ICase
                           match printer. *)
                        :: str ", _ => panic!(\"non-exhaustive match\")"
                        :: [str "}"]
                      )
                    | _ =>
                    ( Pretty.block_enclose (
                        Pretty.block (
                          (str "match"
                          :: Pretty.brk 1
                          :: to_tuple dummy_parms ((Pretty.block o commas) dummy_parms)
                          :: Pretty.brk 1
                          :: [str "{"])
                        ),
                        str "}"
                      )
                      (* catch-all: HOL functions may be partial, but Rust matches
                         must be total (e.g. `nth [] n` has no clause). *)
                      (commas_append (map (print_eqn false) eqs
                        @ [str "_ => panic!(\"non-exhaustive match\")"]))
                    ))])
                  end;
            val prolog =
              case impl_method
               of NONE => concat [str ("pub "^definer), (str o deresolve_const) const, generics]
                | SOME method_name => (concat o map str) [definer, method_name]
          in pair
            (print_val_decl print_typscheme (Constant const, vs_ty))
            (concat (
              prolog
              :: [print_eqns vs_ty (is_pseudo_fun (Constant const)) eqs]
            ))
          end;
    (** Top-level statement dispatcher: routes each stmt variant to its printer.
        Exc -> exception stub, Val -> single binding, Funs -> function group,
        Datas -> enum declarations, Class -> trait declaration, Inst -> impl block. **)
    (*fun print_stmt: Code_Namespace.export -> stmt -> Pretty.T list * Pretty.T*)
     fun print_stmt _ (Exc (const, (vs_ty, n))) = pair
          [print_val_decl print_typscheme (Constant const, vs_ty)]
          (String.concat (
            "let"
            :: deresolve_const const
            :: replicate n "_"
            @ "="
            :: "failwith"
            @@ print_rust_string const
          ) 
          |> str)
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
            (* FIXME (P3): a self-referential nullary value is emitted as a thunk
               `fn x()` plus this module-level `let x = x();`, which is not valid
               Rust at item scope. A correct encoding needs a global is_pseudo_fun
               so every use site (across SCCs) calls `x()` consistently; deferred.
               Pseudo-funs only arise from non-conservative definitions
               (partial_function / codatatypes), which the test suite does not use,
               so this path is currently unexercised. The `();` here is at least
               single- rather than double-semicolon. *)
            fun print_pseudo_fun sym = concat [
                str "let",
                (str o deresolve) sym,
                str "=",
                (str o deresolve) sym,
                str "();"
              ];
            val head = "fn";
            val (sig_ps, (ps, p)) = (apsnd split_last o split_list)
              (print_def' head binding :: map (print_def' head o snd) exports_bindings);
            val pseudo_ps = map print_pseudo_fun pseudo_funs;
          in pair
            (map_filter (fn (export, p) => if Code_Namespace.not_private export then SOME p else NONE)
              ((export :: map fst exports_bindings) ~~ sig_ps))
            (Pretty.chunks2 (ps @ p :: pseudo_ps))
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
              Pretty.block_enclose(
                Pretty.block(
                  str "pub trait "
                  :: print_dicttyp (class, ITyVar v)
                  :: print_super_traits classrels
                  :: [str " {"]),
                str "}"
              )
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
     | print_stmt _ (Inst ((class, tyco), (vs, methods))) =
          let
            (** "impl<A : Clone + Bound, ..> Class for Tyco<A, ..>" header. **)
            val header = concat [
              str "impl",
              print_impl_generics vs,
              str (deresolve_class class),
              str " for ",
              print_tyco_expr (Type_Constructor tyco, map (ITyVar o fst) vs)
            ]
            (** Fetch and eta-normalize the implementing constant's equations
                from the (untouched) program, so its body can be inlined as the
                trait method. Mirrors binding_of_stmt's eta-expansion. **)
            fun method_function const_sym =
              case lookup_constant_fun const_sym
               of SOME ((tysm as (mvs, mty), raw_eqs), _) =>
                    let
                      val eqs = filter (snd o snd) raw_eqs
                      val eqs' =
                        if null (filter_out (null o snd) mvs)
                        then case eqs
                          of [(([], t), some_thm)] =>
                              if (not o null o fst o Code_Thingol.unfold_fun) mty
                              then [(([IVar (SOME "x")], t `$ IVar (SOME "x")), some_thm)]
                              else eqs
                           | _ => eqs
                        else eqs
                    in SOME (tysm, eqs') end
                | NONE => NONE
            fun print_method (classparam, method_sym) =
              let
                val const_s = (fn Constant s => s | sym => deresolve sym) method_sym
                (* A method name inside `impl Trait for T { fn .. }` must be the
                   bare trait-method name, never crate-qualified. *)
                val method_name = deresolve_base (Constant classparam)
              in
                case method_function method_sym
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
            val provided_cps = map fst methods
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
                                  [str (" { " ^ deresolve (Type_Constructor tyco)
                                        ^ "::" ^ deresolve_base csym ^ " }")]
                              | NONE =>
                                  [str (" { panic!(\"unimplemented instance method: "
                                        ^ nm ^ "\") }")])
                        in SOME (print_method_sig nm mty cls_v tail) end)
                      all_cps)
          in pair
            []
            (Pretty.block_enclose (Pretty.block [header, str " {"], str "}")
              (map print_method methods @ stub_methods))
          end;
  in print_stmt end;

(** print module **)

(** Print a Rust module: prepend `use` statements to the body.
    `includes` are external crates, imported with a glob (`use num_bigint::*;`).
    `trait_uses` are explicit crate-internal paths (e.g. "crate::HOL::Equal") for
    the traits this module needs in scope so that `Type::method` trait-method
    dispatch resolves; every other cross-module reference is already fully
    crate::-qualified, so no module-glob import is emitted. **)
fun print_rust_module name decls trait_uses includes body =
  let
    (* Import the BigInt support crates (num_bigint / num_traits::sign) only for
       files that actually use BigInt, so the `use ...::*;` globs stay out of
       files that map integers nowhere. The integer mapping (Rust_Setup.thy) and
       numeral literals both surface the substring "BigInt", so a per-file body
       scan covers every use site. *)
    val bigint_includes = ["num_bigint", "num_traits::sign"]
    val uses_bigint =
      List.exists (fn p => String.isSubstring "BigInt" (Pretty.string_of p)) body
    val includes' =
      if uses_bigint then includes
      else filter_out (member (op =) bigint_includes) includes
    val includes_p = Pretty.chunks (map (fn i => str ("use "^i^"::*;")) includes')
    val trait_uses_p = Pretty.chunks (map (fn p => str ("use "^p^";")) trait_uses)
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
      @ (if List.null trait_uses then [] else [trait_uses_p])
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
fun rust_program_of_program ctxt module_name reserved identifiers (inst_method_syms, inst_table) closure_inst_data =
  let
    (** A constant that implements a polymorphic instance method: its body is
        inlined into the generated impl block (see the Inst printer), so it must
        not be emitted as a standalone top-level function. **)
    fun is_inst_method sym = member (op =) inst_method_syms sym;
    (** If sym is the chosen representative of an instance, the Inst stmt to emit
        in its place (carrying every method of that instance). **)
    fun repr_inst sym = AList.lookup (op =) inst_table sym;
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
    fun binding_of_stmt (sym as Constant const, (export, Code_Thingol.Fun ((tysm as (vs, ty), raw_eqs), _))) =
          let
            val eqs = filter (snd o snd) raw_eqs;
            val (eqs', some_sym) = if null (filter_out (null o snd) vs) then case eqs
               of [(([], t), some_thm)] => if (not o null o fst o Code_Thingol.unfold_fun) ty
                  then ([(([IVar (SOME "x")], t `$ IVar (SOME "x")), some_thm)], NONE)
                  else (eqs, SOME (sym, member (op =) (Code_Thingol.add_constsyms t []) sym))
                | _ => (eqs, NONE)
              else (eqs, NONE)
          in ((export, Function (const, (tysm, eqs'))), some_sym) end
      | binding_of_stmt (sym, _) =
          error ("Binding block containing illegal statement: " ^
            Code_Symbol.quote ctxt sym)
    (** For a group of statements, emit one Inst (impl block) for each instance
        whose representative constant appears in the group. **)
    fun emit_insts stmts =
      map_filter (fn (sym, (export, _)) =>
        Option.map (fn data => SOME (export, Inst data)) (repr_inst sym)) stmts;
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
        (* Emit each datatype's missing superclass-closure impls right beside it.
           A datatype is declared in exactly one group, so this needs no
           cross-group de-duplication; closure_inst_data is already distinct. *)
        val closure_stmts =
          maps (fn (export, (tyco, _)) =>
            map_filter (fn (cls, t, vs) =>
              if t = tyco then SOME (SOME (export, Inst ((cls, t), (vs, [])))) else NONE)
              closure_inst_data)
            datas
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
          then (case repr_inst sym of SOME data => [SOME (export, Inst data)] | NONE => [])
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
      cyclic_modules = false, class_transitive = true,
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
    val rust_lints = if rust_lints = "" then "unused = \"allow\"\nnonstandard_style = \"allow\"" else rust_lints;

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
                          (* Require const = `<classparam>_<tyco>` even for a
                             single-method class, so an auxiliary function that
                             merely shares the `<class>_<tyco>_inst` segment is
                             not mistaken for the method. *)
                          val cp_opt =
                            Option.map fst (find_first (fn (cp, _) =>
                              after_last_dot const = after_last_dot cp ^ "_" ^ after_last_dot tyc) cps)
                        in Option.map (fn cp => (inst_s, (cls, tyc, vs, cp, sym))) cp_opt end
                  end
              end
          | _ => NONE)
          stmt_list
      end;

    (** All instance-method constants (suppressed as standalone functions). **)
    val inst_method_syms = map (fn (_, (_, _, _, _, sym)) => sym) inst_methods;
    (** One impl per instance, keyed by a representative method constant; the
        Inst payload carries (class, tyco), the instance vs, and every method. **)
    val inst_table =
      map (fn seg =>
        let
          val members = filter (fn (s, _) => s = seg) inst_methods
          val (_, (cls, tyc, vs, _, repr_sym)) = hd members
          val methods = map (fn (_, (_, _, _, cp, msym)) => (cp, msym)) members
        in (repr_sym, ((cls, tyc), (vs, methods))) end)
        (distinct (op =) (map fst inst_methods));

    (** Map each reconstructed instance-method constant to (tyco, classparam):
        the concrete type it is implemented for and the trait method it realizes.
        Used at call sites to emit `Tyco::<trait_method>(..)`. **)
    val inst_method_lookup =
      maps (fn (_, ((_, tyc), (_, methods))) =>
        map (fn (cp, msym) => (msym, (tyc, cp))) methods) inst_table;
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
        (* A (class, tyco) is already provided either by a reconstructed Fun
           instance or by a constructor-backed one; the closure pass must not also
           stub it. *)
        val provided_ct = distinct (op =) (reconstructed_ct @ constr_inst_ct)
        fun datatype_vs t =
          (case Code_Symbol.Graph.get_node program (Type_Constructor t) of
              Code_Thingol.Datatype (vns, _) => map (fn v => (v, [])) vns
            | _ => [])
          handle Code_Symbol.Graph.UNDEF _ => [];
        val tyco_vs = map (fn (_, ((_, t), (vs, _))) => (t, vs)) inst_table
        fun vs_of_tyco t =
          (case AList.lookup (op =) tyco_vs t of SOME vs => vs | NONE => datatype_vs t)
        val missing =
          distinct (op =)
            (maps (fn (c, t) =>
               map_filter (fn s =>
                 if class_nonempty s andalso not (member (op =) provided_ct (s, t))
                 then SOME (s, t) else NONE)
                 (supers_closure c))
               reconstructed_ct)
        (* Constructor-backed instances are emitted here too (with the constructor
           filled in as the method body by the Inst printer), so the impl is
           present even when no superclass closure references it. Drop any that a
           Fun instance already reconstructs — that impl's stub pass fills the
           constructor body, and emitting it again would be a duplicate impl. *)
        val all_pairs =
          distinct (op =)
            (missing @ filter_out (member (op =) reconstructed_ct) constr_inst_ct)
      in map (fn (s, t) => (s, t, vs_of_tyco t)) all_pairs end;

    (* build program *)
    val { deresolver, hierarchical_program = rust_program } =
      rust_program_of_program ctxt module_name (Name.make_context reserved_syms)
        identifiers (inst_method_syms, inst_table) closure_inst_data exports program;


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
      end; 
    val lookup_constant_typeco = lookup_constant_typeco_gen program;
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
      
    (** Compute module-level import dependencies:
        for each module, collect the set of other modules it depends on.
        Module names must come from the namespace deresolver so code_identifier
        remappings such as Nat/Power -> Arith are respected. **)
    val generated_modules =
      Code_Namespace.print_hierarchical {
        print_module = fn _ => fn base => fn _ => fn _ => base,
        print_stmt = fn _ => fn _ => "",
        lift_markup = K I } rust_program
      |> filter (fn s => s <> "")
      |> distinct (op =)
    val module_imports =
      let
        fun before_first_dot s =
          (case (String.fields (fn c => c = #".") s) 
            of [] => s
            | x::_ => x)
        fun is_generated_module module =
          List.exists (fn module' => module' = module) generated_modules
        fun get_sym_module sym = before_first_dot (deresolver [] sym)
        fun get_import_sym sym = 
          let 
            val module = get_sym_module sym
            val children = Code_Symbol.Graph.immediate_succs program sym
            fun add_dpdnc sym' dpdncs =
              if List.exists (fn x => x = (get_sym_module sym')) dpdncs then dpdncs
              else (get_sym_module sym')::dpdncs  
          in
            (module, fold add_dpdnc children [])  
          end
        fun get_imports sym imports = 
          let 
            val (module, import) = get_import_sym sym
          in
            if (List.exists (fn (mdl, _) => (mdl = module)) imports)
            then (map (fn (mdl, import') => 
              if (mdl = module) 
              then (mdl, distinct (op =) (import @ import'))
              else (mdl, import'))
              imports)
            else (module, import)::imports
          end
        val mod_dpdncs = fold get_imports (map fst sym_dpdnc_list) []
        val mod_imports = map (fn (sym, dpdncs) =>
          (sym, filter (fn x => x <> sym andalso is_generated_module x) dpdncs)) mod_dpdncs
      in
        filter (is_generated_module o fst) mod_imports
      end
      val raw_modules = generated_modules

    (** For each module, the crate-paths of the traits it DEFINES, keyed by
        module name. A module that depends on another only needs that module's
        *traits* in scope (for `Type::method` dispatch), emitted as explicit
        `use crate::<mod>::<Trait>;`; everything else is referenced by a
        fully-qualified `crate::` path. **)
    val module_to_traits =
      let
        fun fields s = String.fields (fn c => c = #".") s
        fun before_first_dot s = (case fields s of x :: _ => x | [] => s)
        fun trait_entry c =
          let val qual = deresolver [] (Type_Class c)
          in (before_first_dot qual, "crate::" ^ String.concatWith "::" (fields qual)) end
      in
        fold (fn (mdl, path) => AList.map_default (op =) (mdl, []) (insert (op =) path))
          (map_filter (fn ((sym, stmt), _) =>
            case (sym, stmt) of
              (Type_Class c, Code_Thingol.Class _) => SOME (trait_entry c)
            | _ => NONE)
            stmt_list)
          []
      end

    (** Map a Code_Namespace resolved name to a Rust path. The deresolver returns
        a dot-separated name relative to the current module: a single segment for
        a local symbol, `Module.base` for a sibling module. Local names stay bare;
        cross-module names become an absolute `crate::Module::base` path, so equal
        base names in different modules stay distinct without relying on glob
        imports to disambiguate them. **)
    fun modify_deresolver deresolver sym =
      (case String.fields (fn c => c = #".") (deresolver sym) of
        [base] => base
      | segs => "crate::" ^ String.concatWith "::" segs)

    (** Print a single statement within its module context. **)
    fun print_stmt prefix_fragments (sym, (export, stmt)) =
      let
        val _ = tracing ("[Thingol] "
          ^ Code_Debug_Info.print_debug_info_sym sym ^ ": "
          ^ Code_Debug_Info.print_debug_info_thingol_stmt (get_node program sym))
      in
        (print_rust_stmt
          tyco_syntax const_syntax (make_vars reserved_syms)
          (Code_Thingol.is_constr program) (modify_deresolver (deresolver prefix_fragments))
          box_table phantom_table
          lookup_constant_typeco lookup_constant_fun
          lookup_method_class inst_method_info lookup_class_methods constr_method_of)
          export stmt
        |> apfst (fn decl => if Code_Namespace.not_private export then SOME decl else NONE)
      end;

    (** Print a module: gather declarations, resolve imports, and wrap in module body. **)
    fun print_module _ base _ xs =
      let
        val (raw_decls, body) = split_list xs;
        val decls = maps these raw_decls
        val dep_modules = filter (fn (sym, _) => (sym = base)) module_imports
          |> (fn mods => case mods of [(_, deps)] => deps | _ => [])
        val trait_uses = distinct (op =)
          (maps (fn dep => these (AList.lookup (op =) module_to_traits dep)) dep_modules)
      in (SOME [str base], print_rust_module base decls trait_uses rust_includes body) end;

    (** Assemble final output: Cargo.toml + main.rs + per-module .rs files.
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
    val main = pair
      (["src", "main.rs"])
      (Pretty.chunks([
        str "#![feature(box_patterns)]",
        str (fold (fn s => (fn acc => ("pub mod "^s^";\n")^acc)) modules "" ),
        str "fn main(){}"
      ]))
  in
    (Code_Target.Hierarchy (toml :: main :: srcs @ empty_mods),
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
    Sets up the serializer, literal syntax, fun type printing, and reserved words. **)
val _ = Theory.setup
  (Code_Target.add_language
    (target, {serializer = serializer_rust, literals = literals_rust,
      check = {env_var = "",
        make_destination = I,
        make_command = fn _ => ""},
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
