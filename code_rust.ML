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

open Code_Debug_Info;

infixr 5 @@;         
infixr 5 @|;


(** generic **)

val target = "Rust";

(** Intermediate binding representation: a single function or class instance definition. **)
datatype binding =
    Function of string * (typscheme * ((iterm list * iterm) * (thm option * bool)) list)
  | Instance of (string * class) * { class: class, tyco: string, vs: (vname * sort) list,
        superinsts: (class * (itype * dict list) list) list,
        inst_params: ((string * (const * int)) * (thm * bool)) list,
        superinst_params: ((string * (const * int)) * (thm * bool)) list };

(** Intermediate statement IR: groups bindings into Rust-level declarations.
    Converted from Code_Thingol stmts by modify_stmts before printing. **)
datatype stmt =
    Exc of string * (typscheme * int)
  | Val of binding
  | Funs of (Code_Namespace.export * binding) list * Code_Symbol.T list
  | Datas of (string * (vname list * ((string * vname list) * itype list) list)) list
  | Class of string * (vname * ((class * class) list * (string * itype) list));

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

(* log-efficiency dedup*)
fun merge leq (L1 : string list, L2 : string list) = case (L1, L2) of
  ([], L2) => L2
  | (L1, []) => L1
  | (x1::rest1, x2::rest2) =>
  if leq(x1, x2) then x1 :: merge leq (rest1, L2)
  else x2 :: merge leq (L1, rest2);
fun mergesort leq (lst : string list) =
  if (length lst) <= 1 then lst
  else
  let 
    val m = (length lst) div 2
    val (L1, L2) = (List.take(lst, m), List.drop(lst, m))
  in
    merge leq (mergesort leq L1, mergesort leq L2)
  end;
fun dedup_sorted eq (lst : string list) = case lst 
  of [] => []
  | [x] => [x]
  | x1 :: x2 :: rest =>
    if eq(x1, x2) then dedup_sorted eq (x2 :: rest)
    else x1 :: dedup_sorted eq (x2 :: rest);
fun dedup (lst : string list) : string list = dedup_sorted (op=) (mergesort (op<=) lst)
(* log-efficiency list minus*)
fun lminus L1 L2 = 
  let
    val l1 = dedup L1 
    val l2 = dedup L2 
    fun minus (x::xs, y::ys) =
          if x = y then minus(xs, ys)
          else if x < y then x :: minus(xs, y::ys)
          else minus(x::xs, ys)
      | minus (xs, []) = xs
      | minus ([], _) = []
  in
    minus (l1, l2)
  end


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

(** Main statement printer: given syntaxes and lookup functions, returns print_stmt.
    Contains all local printers for types, terms, patterns, cases, defs, and stmts.
    Parameters:
      tyco_syntax/const_syntax: user-registered custom syntax overrides
      reserved: reserved name context
      is_constr: test if a symbol is a constructor
      deresolve: resolve qualified symbol to its printed Rust name
      is_inf_typeco: test if a type constructor contains recursive references (needs Box)
      is_invdependent_typecos: for each constructor arg, whether it needs Box wrapping
      lookup_constant_typeco: look up which type constructor a constant belongs to
      lookup_constant_fun: look up the exact definition of 
      lookup_class_methods: get method list of a type class
      lookup_method_class: get the class of a class method **)
fun print_rust_stmt tyco_syntax const_syntax reserved is_constr deresolve 
  is_inf_typeco is_invdependent_typecos 
  lookup_constant_typeco lookup_constant_fun
  lookup_class_methods lookup_method_class =
  let
    val deresolve_const = deresolve o Constant;
    val deresolve_typco = deresolve o Type_Constructor;
    val deresolve_class = deresolve o Type_Class;
    val deresolve_classrel = deresolve o Class_Relation;
    val deresolve_inst = deresolve o Class_Instance;
    fun box s = "Box<"^s^">"
    fun clone s = s^".clone()"
    fun box_new s = "Box::new("^s^")"
    fun box_pattern s = "box "^s
    fun to_upper s = (String.implode (map Char.toUpper (String.explode s)))
    (** Print a type constructor application, inserting Box<> for recursive types. **)
    fun print_tyco_expr_gen tyco_op is_head (sym, tys) = 
      let
        val isinf = (case tyco_op 
          of NONE => false
          | (SOME co) => is_inf_typeco co sym)
        val tyconame = deresolve sym
      in
        (if (isinf andalso (not is_head)) 
        then (fn prt => str (box (Pretty.string_of prt))) 
        else I)
        (case tys  
        of [] => str tyconame                                                      
        | tys =>
          Pretty.block(
            str tyconame
            :: str "<"
            :: enum "," "" "" (map (print_typ_gen NONE true BR) tys)
            :: [str ">"]
          ))
      end
    (** Print an itype to Rust type syntax.
        Dispatches to custom tyco_syntax or default print_tyco_expr_gen. **)
    and print_typ_gen tyco_op is_head fxy (tyco `%% tys) = (case tyco_syntax tyco
         of NONE => print_tyco_expr_gen tyco_op is_head (Type_Constructor tyco, tys)
          | SOME (_, print) => print (print_typ_gen tyco_op is_head) fxy tys)
      | print_typ_gen _ _ _  (ITyVar v) =
        str (to_upper v);
    fun print_tyco_expr (sym, tys) = print_tyco_expr_gen NONE true (sym, tys);
    fun print_typ fxy ty = print_typ_gen NONE true fxy ty;
    fun print_dicttyp (class, ty) = print_tyco_expr (Type_Class class, []); (*omit generic param Self*)
    (** Print a trait method signature: "fn method(params) -> RetType;" **)
    fun print_trait_typ fxy class ty generic_ty =
      let
        val self_ty_s = (fn ITyVar v => to_upper v) generic_ty
        val ts = extract_typ print_typ ty
          |> map (fn p => (if (Pretty.string_of p) = self_ty_s then str "Self" else p))
        val param_num = (List.length ts) - 1
        val ret_typ = List.last ts 
        val param_typs = List.take (ts, param_num)
        fun print_dummy_params param_num =
          let fun aux param_num index param_l =
            if index < param_num 
            then "x"^(Int.toString index)::(aux param_num (index+1) param_l)
            else param_l
          in aux param_num 0 [] end
        val params = map (fn (s, p) => Pretty.block[str (s^": "), p])
          (ListPair.zip ((print_dummy_params param_num), param_typs))
      in  
        Pretty.block(
          str "fn "
          :: str (deresolve_const class)
          :: enum "," " (" ")" params
          :: str " -> "
          :: ret_typ
          :: [str ";"]
        )
      end;
    (** Print type scheme prefix: where-clause with trait bounds from sort annotations. **)
    fun print_typscheme_prefix (vs, p) = enum " ->" "" ""
      (map_filter (fn (v, sort) =>
        (print_product (fn class => print_dicttyp (class, ITyVar v)) sort)) vs @| p);
    fun print_typscheme (vs, ty) = print_typscheme_prefix (vs, print_typ NOBR ty);
    fun print_dicttypscheme (vs, class_ty) = print_typscheme_prefix (vs, print_dicttyp class_ty);
    (** Print dictionary (type class witness) terms. **)
    val print_classrels =
      fold_rev (fn classrel => fn p => p)
    fun print_dict is_pseudo_fun fxy (Dict (classrels, x)) =
      print_plain_dict is_pseudo_fun fxy x
      |> print_classrels classrels
    and print_plain_dict is_pseudo_fun _ (Dict_Const (inst, dss)) =
          brackify BR ((str o deresolve_inst) inst ::
            (if is_pseudo_fun (Class_Instance inst) then [str "()"]
            else map_filter (print_dicts is_pseudo_fun BR o snd) dss))
      | print_plain_dict _ _ (Dict_Var { var, index, length, ... }) =
          str (if length = 1 then Name.enforce_case true var ^ "::"
            else Name.enforce_case true var ^ string_of_int (index + 1) ^ "::")
    and print_dicts is_pseudo_fun = tuplify (print_dict is_pseudo_fun);
    val print_dict_args = map_filter (fn (v, sort) => print_dicts (K false) BR
      (map_index (fn (i, _) => Dict ([],
         Dict_Var { var = v, index = i, length = length sort, class = nth sort i, unique = true })) sort));
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
          then str (box_prcs (clone_prcs (lookup_var vars v)))
          else str (clone_prcs (lookup_var vars v))
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
                  Pretty.block(
                    print_term_decl is_pseudo_fun some_thm vars NOBR t'
                    :: str " ("
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
        fun print_cons (SOME s) =
          let 
            fun after_last_dot s =
              (case List.rev (String.fields (fn c => c = #".") s) of
                  [] => s
                | x::_ => x)
            in to_upper_camel_case (after_last_dot s) end
        | print_cons NONE = ""
        val typeco_s = print_cons (lookup_typeco t)
        fun typeco_append co_s t_s = 
          if co_s = "" then t_s
          else co_s^"::"^t_s 
        val term = print_term t
        val term_with_cons = typeco_append typeco_s (Pretty.string_of term)
        val term_with_box = 
          if need_box 
          then (box_prcs term_with_cons) 
          else term_with_cons
      in
        str term_with_box
      end
    (** Print a function/constructor application expression.
        Handles constructors (with Box wrapping per argument),
        pseudo-functions, and regular functions (with generic prefix for trait dispatch). **)
    and print_app_expr is_pseudo_fun (box_prcs, clone_prcs)
       some_thm vars (app as ((const as { sym, dicts, dom, range, ... }), ts)) =
        if is_constr sym then
          let 
            val wanted = length dom
            val need_box_list = is_invdependent_typecos const
          in
            if wanted = 0
            then [(str o deresolve) sym]
            else if length ts = wanted
            then
              (str o deresolve) sym 
              :: [Pretty.block (
                str "("
                :: (commas_append 
                    (map 
                    (fn (t, need_box) => 
                      (print_term_gen is_pseudo_fun (need_box, box_prcs, clone_prcs) some_thm vars NOBR t)) 
                    (ListPair.zip (ts, need_box_list))))
                @ [str ")"]
                )]
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
            val generic_prefixs =
              if (List.null dicts) orelse (List.all (fn xs => List.null xs) dicts)
              then []
              else (case prefix_target_ty of
                  ("fun" `%% _) => []
                | ty => [Pretty.block [print_generic_prefix_typ ty, str "::"]])
            fun deresolve_trait_impl sym = 
              let
                fun after_last_dot s = 
                  (case List.rev (String.fields (fn c => c = #".") s) 
                    of [] => s
                    | x::_ => x)
                fun before_last_dot s =
                  (case List.rev (String.fields (fn c => c = #".") s) 
                    of x1::x2::_ => x2
                    | _ => s)
                fun print_plain_typ _ (ITyVar v) = v
                  | print_plain_typ _ (tyco `%% tys) = tyco
                val inst_s = before_last_dot ((fn Constant s => s) sym)
                val typs_s_l = map (print_plain_typ NOBR) (if List.null dom then [range] else dom)
                fun extract_class_dict (Code_Thingol.Dict (classrels, plain_dict)) =
                  extract_class_plain_dict plain_dict :: map snd classrels
                and extract_class_plain_dict (Code_Thingol.Dict_Var {var, index, length, class, ...}) = class
                  | extract_class_plain_dict (Code_Thingol.Dict_Const ((_, class), _)) = class
                val classes_s_l = List.concat (map extract_class_dict (List.concat dicts))
                val classes_methods_s_l = map 
                  (fn s => (s, 
                    (dedup o (map fst) o (lookup_class_methods print_plain_typ) o (fn x => (Type_Class x))) s)) 
                  classes_s_l
                fun pred xs ys = List.concat (List.map (fn x => List.map (fn y => (x, y)) ys) xs)
              in
                (fn xs => if List.null xs then (str o deresolve) sym
                else (str o deresolve_const o List.hd) xs)
                (map_filter
                  (fn ((cls_s, mthd_s_l), typ_s) => 
                    if ((after_last_dot cls_s)^"_"^(after_last_dot typ_s)^"_inst" = inst_s) 
                    then (SOME (List.hd mthd_s_l)) else NONE)
                  (pred classes_methods_s_l typs_s_l))            
              end 
            val funcname = 
              if List.null generic_prefixs then (str o deresolve) sym 
              else deresolve_trait_impl sym 
          in
            if length ts = wanted_app
            then
              let 
                val (ts1, ts2) = chop wanted_fn ts
              in 
                [Pretty.block (
                  generic_prefixs
                  @ funcname
                  :: str "("
                  :: (commas_append
                      (map 
                        (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR)
                      ts1))
                  @ str ")"
                  :: (if List.null ts2 
                      then [str ""]
                      else
                        str "(" 
                        :: (commas_append
                            (map 
                              (print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR)
                            ts2))
                        @ [str ")"]
                      )
                )]
              end
            else
              let 
                val saturated_t = Code_Thingol.saturated_application wanted_app app
              in
                [print_term_gen is_pseudo_fun (false, box_prcs, clone_prcs) some_thm vars NOBR saturated_t]
              end 
          end
    and print_app is_pseudo_fun some_thm vars = 
      gen_print_app (print_app_expr is_pseudo_fun (I, I))
      (print_term_decl is_pseudo_fun) const_syntax some_thm vars
    and print_app_with_clone is_pseudo_fun (box_prcs, clone_prcs) some_thm vars =
      gen_print_app (print_app_expr is_pseudo_fun (box_prcs, clone_prcs))
      (print_term_decl is_pseudo_fun) const_syntax some_thm vars
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
            (commas_append (map print_select clauses))
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
        val closure_pretty =
          Pretty.block_enclose (
            Pretty.block (
              str "(move |"
              :: commas_append
                (map (fn (p1, p2) => str ((Pretty.string_of p1)^": "^(Pretty.string_of p2)))
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
    fun print_val_decl print_typscheme (sym, typscheme) = concat
      [str "val", str (deresolve sym), str ":", print_typscheme typscheme];
    (** Print a Rust enum declaration with #[derive(Clone)].
        Each constructor becomes an enum variant. **)
    fun print_datatype_decl definer (tyco, (vs, cos)) =
      let
        fun print_co ((co, _), []) = str (deresolve_const co)
          | print_co ((co, _), tys) = 
            concat [
              str (deresolve_const co), 
              Pretty.block(
                [
                str "(",
                enum "," "" "" (map (print_typ_gen (SOME tyco) false (INFX (2, X))) tys), 
                str")"]
              )
              ];
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
    (** Print a function or instance definition.
        For Function: emits fn signature with generics, trait bounds, and
        either a direct expression, single-arm match, or multi-arm match body.
        For Instance: emits impl block (currently legacy/unused path). **)
    fun print_def is_pseudo_fun needs_typ definer
          (Function (const, (vs_ty as (vs, ty), eqs))) =
          let
            fun to_tuple l prt = if (length l >= 2) then Pretty.block ([str "(", prt, str ")"]) else prt;
            fun is_inst const (vs, ty) = 
              let
                fun after_last_dot s = 
                  (case List.rev (String.fields (fn c => c = #".") s) 
                    of [] => s
                    | x::_ => x)
                fun before_last_dot s =
                  (case List.rev (String.fields (fn c => c = #".") s) 
                    of x1::x2::_ => x2
                    | _ => s)
                fun print_plain_typ _ (ITyVar v) = v
                  | print_plain_typ _ (tyco `%% tys) = tyco
                val inst_s = before_last_dot const
                val classes_s_l = dedup (List.concat (map snd vs))
                val classes_methods_s_l = map 
                  (fn s => (s, 
                    (dedup o (map fst) o (lookup_class_methods print_plain_typ) o (fn x => (Type_Class x))) s)) 
                  classes_s_l
                val typs_s_l = dedup (extract_typ print_plain_typ ty)
                fun pred xs ys = List.concat (List.map (fn x => List.map (fn y => (x, y)) ys) xs)
              in
                map_filter
                  (fn ((cls_s, mthd_s_l), typ_s) => 
                    if ((after_last_dot cls_s)^"_"^(after_last_dot typ_s)^"_inst" = inst_s) 
                    then (SOME (List.hd mthd_s_l, typ_s)) else NONE)
                  (pred classes_methods_s_l typs_s_l)    
              end
            val impl_method_typ_l = is_inst const (vs, ty)
            val is_impl = ((List.length impl_method_typ_l) = 1)
            val impl_method_typ_op = if is_impl then (fn [(m, t)] => SOME (m, t)) impl_method_typ_l else NONE
            (** Compute generic parameters <A, B> and where-clause trait bounds
                from the type variables and sort constraints. **)
            fun print_generics_and_traits vs ty = 
              let
                fun extract_generics t =
                  let
                    fun aux (ITyVar v, acc) = to_upper v :: acc
                      | aux ((_ `%% tys), acc) = List.foldl aux acc tys
                  in aux (t, []) end
                val generic_params = dedup (extract_generics ty)
                fun print_traits vs generic_params = 
                  let
                    fun print_vs_traits vs = 
                      map 
                      (fn (vname, sort) =>
                        Pretty.block(
                          str ((to_upper vname)^" : Clone")
                          :: [if List.null sort
                            then str ""
                            else enum " +" " + " ""  (map (fn s => print_tyco_expr (Type_Class s, [])) sort)]
                        )
                      )
                      vs
                    val vl = map to_upper (map fst vs)
                    val other_traits = 
                      map_filter 
                      (fn s => 
                        if List.exists (fn s' => (s' = s)) vl
                        then NONE
                        else SOME (str (s^" : Clone")))
                      generic_params
                  in
                     commas_append ((print_vs_traits vs) @ other_traits)
                  end
              in
                pair
                (if List.null generic_params
                then str ""
                else if not is_impl 
                then enum "," "<" ">" (map str generic_params)
                else enum "" "<" ">" (print_traits vs generic_params)
                )
                (if List.null generic_params
                then str ""
                else if not is_impl
                then 
                  Pretty.block_enclose (str "where",str "")
                  (print_traits vs generic_params)
                else str "")
              end;
            val (generics, traits) = print_generics_and_traits vs ty;
            (** Print a single equation as a match arm: "pattern => expr".
                If is_degenerated (single clause), prints just the expression body. **)
            fun print_eqn is_degenerated ((ts, t), (some_thm, _)) =
              let
                val vars = reserved
                  |> intro_base_names_for (is_none o const_syntax)
                      deresolve (t :: ts)
                  |> intro_vars (build (fold Code_Thingol.add_varnames ts));
                fun add_boxed_list t boxed_list = 
                  (case (Code_Thingol.unfold_const_app t)
                  of (SOME (const, ts as (_::_))) => 
                    (let 
                      val boxed_l = is_invdependent_typecos const
                      fun add (t::ts) (b::boxed_l') boxed_list = 
                        if b 
                        then t::(add ts boxed_l' boxed_list) 
                        else add ts boxed_l' boxed_list
                      | add [] [] boxed_list = boxed_list
                    in
                      add ts boxed_l boxed_list
                    end)
                  | _ => boxed_list)
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
            (** Wrap a function body in "impl Trait for Type { ... }" block. **)
            fun print_impl ty generics impl_method_typ_op prt = 
              let 
                fun except_after_last_dot s = 
                  (case List.rev (String.fields (fn c => c = #".") s) 
                    of [] => s
                    | x::xs => String.concatWith "." xs)
                val (mthd_s, impl_typ_s) = (fn SOME x => x) impl_method_typ_op
                val impl_typ_s' = deresolve_typco impl_typ_s
                val typs_s = dedup (map Pretty.string_of (extract_typ print_typ ty))
                val impl_typ = str (List.hd (filter (fn s => String.isSubstring impl_typ_s' s) typs_s))
              in
                Pretty.block_enclose (
                  Pretty.block (
                    str "impl"
                    :: generics
                    :: Pretty.brk 1
                    :: str (deresolve_class
                      (lookup_method_class (Code_Symbol.Constant mthd_s)))
                    :: str " for "
                    :: impl_typ
                    :: [str " {"]
                  ),
                  str "}"
                )
              end
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
                          Pretty.block(
                            str "impl Fn"
                            :: enum "," "(" ")" params
                            :: str " -> "
                            :: [ret]
                          )
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
                      (commas_append (map (print_eqn false) eqs))
                    ))])
                  end;
            val prolog = 
              if (not is_impl) 
              then concat [str ("pub "^definer), (str o deresolve_const) const, generics]
              else (concat o map str) [definer, deresolve_const ((fn SOME (m, t) => m) impl_method_typ_op)]
          in pair
            (print_val_decl print_typscheme (Constant const, vs_ty))
            ((if is_impl then (print_impl ty generics impl_method_typ_op) else I)
            concat (
              prolog
              :: [print_eqns vs_ty (is_pseudo_fun (Constant const)) eqs]
            ))
          end
      | print_def is_pseudo_fun _ definer
          (Instance (inst as (tyco, class), { vs, superinsts, inst_params, ... })) =
          let
            fun print_super_instance (super_class, dss) =
              concat [
                (str o deresolve_classrel) (class, super_class),
                str "=",
                print_dict is_pseudo_fun NOBR (Dict ([], Dict_Const ((tyco, super_class), dss)))
              ];
            fun print_classparam_instance ((classparam, (const, _)), (thm, _)) =
              concat [
                (str o deresolve_const) classparam,
                str "=",
                print_app (K false) (SOME thm) reserved NOBR (const, [])
              ];
          in pair
            (print_val_decl print_dicttypscheme
              (Class_Instance inst, (vs, (class, tyco `%% map (ITyVar o fst) vs))))
            (concat (
              str definer
              :: (str o deresolve_inst) inst
              :: (if is_pseudo_fun (Class_Instance inst) then [str "()"]
                  else print_dict_args vs)
              @ str "="
              @@ brackets [
                enum_default "()" ";" "{" "}" (map print_super_instance superinsts
                  @ map print_classparam_instance inst_params),
                str ":",
                print_dicttyp (class, tyco `%% map (ITyVar o fst) vs)
              ]
            ))
          end;
    (** Top-level statement dispatcher: routes each stmt variant to its printer.
        Exc -> exception stub, Val -> single binding, Funs -> function group,
        Datas -> enum declarations, Class -> trait declaration. **)
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
            val (sig_p, p) = print_def (K false) true "fn" binding
          in pair
            [sig_p]
            (p)
          end
      | print_stmt _ (Funs ((export, binding) :: exports_bindings, pseudo_funs)) =
          let
            val print_def' = print_def (member (op =) pseudo_funs) false;
            fun print_pseudo_fun sym = concat [
                str "let",
                (str o deresolve) sym,
                str "=",
                (str o deresolve) sym,
                str "();;"
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
     | print_stmt _ (Datas [(tyco, (vs, []))]) =
          let
            val ty_p = print_tyco_expr (Type_Constructor tyco, map ITyVar vs);
          in
            pair
            [concat [str "type", ty_p]]
            (concat [str "type", ty_p, str "=", str "EMPTY__"])
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
              print_trait_typ NOBR class ty (ITyVar v) 
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
          in pair
           (if Code_Namespace.is_public export
              then [trait_decl_p]
              else if null classrels andalso null classparams
              then [trait_decl_p] (*work around weakness in export calculation*)
              else [concat [str "type", print_dicttyp (class, ITyVar v)]])
          (trait_decl_p)
          end;
  in print_stmt end;

(** print module **)

(** Print a Rust module: prepend "use crate::.." import statements to the body. **)
fun print_rust_module name decls imports includes body =
  let 
    val includes_p = Pretty.chunks (map (fn i => str ("use "^i^"::*;")) includes)
  in
    Pretty.chunks2 (
      if List.null imports 
      then includes_p :: body
      else (includes_p 
      :: Pretty.chunks (map (fn i => str ("use crate::"^i^"::*;")) imports) 
      :: body)
    )
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
fun rust_program_of_program ctxt module_name reserved identifiers =
  let
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
    (** Convert a Thingol Fun/Classinst statement into a Function/Instance binding.
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
      | binding_of_stmt (sym as Class_Instance inst, (export, Code_Thingol.Classinst (stmt as { vs, ... }))) =
          ((export, Instance (inst, stmt)),
            if forall (null o snd) vs then SOME (sym, false) else NONE)
      | binding_of_stmt (sym, _) =
          error ("Binding block containing illegal statement: " ^ 
            Code_Symbol.quote ctxt sym)
    (** Convert a single Fun/Classinst into a stmt: Exc (no equations), Val, or Funs. **)
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
    (** Convert a group of mutually recursive functions into a single Funs stmt. **)
    fun modify_funs stmts = single (SOME
      (Code_Namespace.Opaque, Funs (map_split binding_of_stmt stmts |> (apsnd o map_filter o Option.map) fst)))
    (** Collect Datatype statements into a single Datas stmt (multi-constructor enum). **)
    fun modify_datatypes stmts =
      let
        val datas = map_filter
          (fn (Type_Constructor tyco, (export, Code_Thingol.Datatype stmt)) => SOME (export, (tyco, stmt)) | _ => NONE) stmts
      in
        if null datas then [] (*for abstract types wrt. code_reflect*)
        else datas
          |> split_list
          |> apfst Code_Namespace.join_exports
          |> apsnd Datas
          |> SOME
          |> single
      end;
    (** Collect Class/Classrel/Classparam statements into a single Class stmt (trait). **)
    fun modify_class stmts =
      let
        val stmts' = map 
          (fn (c', (_, stmt')) => (c', stmt')) stmts
      in
        the_single (map_filter
          (fn (Type_Class class, (export, Code_Thingol.Class stmt)) => SOME (export, (class, stmt)) | _ => NONE) stmts)
        |> apsnd Class
        |> SOME
        |> single
      end;
    (** Dispatch statement groups by kind to the appropriate modify_* handler.
        Filters out case combinators from function stmts. **)
    fun modify_stmts ([stmt as (_, (_, stmt' as Code_Thingol.Fun _))]) =
          if Code_Thingol.is_case stmt' then [] else [modify_fun stmt]
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Fun _)) :: _)) =
          modify_funs (filter_out (Code_Thingol.is_case o snd o snd) stmts)
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
      | modify_stmts ([stmt as (_, (_, Code_Thingol.Classinst _))]) =
          [modify_fun stmt]
      | modify_stmts ((stmts as (_, (_, Code_Thingol.Classinst _)) :: _)) =
          modify_funs stmts
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

    val _ = tracing ("PROGRAM="^String.concatWith "\n" (map print_debug_info_node stmt_list)^"\n")

    val rust_module = if rust_module = "" then "\"isabelle_exported\"" else rust_module;
    val rust_version = if rust_version = "" then "\"0.1.0\"" else rust_version;
    val rust_edition = if rust_edition = "" then "\"2024\"" else rust_edition;
    val rust_dependencies = if rust_dependencies = "" then "num-bigint = \"0.4.6\"\nnum-traits = \"0.2.19\"" else rust_dependencies;
    val rust_lints = if rust_lints = "" then "unused = \"allow\"\nnonstandard_style = \"allow\"" else rust_lints;

    val rust_includes = "num_bigint" :: "num_traits::sign" :: rust_includes

    (* build program *)
    val { deresolver, hierarchical_program = rust_program } =
      rust_program_of_program ctxt module_name (Name.make_context reserved_syms)
        identifiers exports program;

    val _ = tracing "Build Program Accomplished"

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
          |> dedup
          | dest_types _ = [] (*raise Fail ("dest_types: "^ print_debug_info_thingol_stmt x)*)
        val drct_dpdncs = dest_types (get_node program sym)
        val snd_dpdncs = drct_dpdncs@dpdncs 
          |> map (fn t => (Type_Constructor t)) 
          |> map (get_node program)
          |> map dest_types
          |> List.concat
          |> (fn l => l@drct_dpdncs@dpdncs)
          |> dedup
      in
        if (List.length dpdncs) = (List.length (snd_dpdncs))
        then dpdncs
        else lookup_dependent_types_h program sym snd_dpdncs
      end;
    fun lookup_dependent_types program sym = lookup_dependent_types_h program sym [];
    (** Test whether type constructor sym contains a (possibly indirect) reference to co.
        If so, values of that type need Box indirection. **)
    fun is_inf_typeco co (sym as (Type_Class _)) = false
      | is_inf_typeco co sym =
      let
        val dpdncs = lookup_dependent_types program sym
      in
        List.exists (fn s => s = co) dpdncs
      end;
    (** For each argument of a data constructor, determine whether it needs Box wrapping
        (i.e., the argument's type transitively references the parent datatype). **)
    fun is_invdependent_typecos {sym as (Constant t), typargs = _, dicts = _, dom, range = _, annotation = _} =
      let 
        fun dest_itype (ITyVar vn) = vn
          | dest_itype (v `%% _ ) = v   
        val dttypcon = (fn (Code_Thingol.Datatypecons x) => x) (get_node program sym)
        val dom_typs = dom
          |> map dest_itype
          |> map (fn x => Type_Constructor x)
        val dom_dpdncs = map (lookup_dependent_types program) dom_typs
      in
        map (List.exists (fn s => s = dttypcon)) dom_dpdncs
    end;
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
    (** Look up the methods of a type class along with their types. **)
    fun lookup_class_methods_gen program print_plain_typ sym = 
      let
        val method_stmt = get_node program sym
        val methods = case method_stmt
          of (Code_Thingol.Class (_, (_, const_funty))) => map (fn (c, ty) => (c, (extract_typ print_plain_typ ty))) const_funty
          | _ => []
      in
        methods
      end
    val lookup_class_methods = lookup_class_methods_gen program
    (** Look up which class a class parameter (method) belongs to. **)
    fun lookup_method_class_gen program sym =
      let
        val class_stmt = get_node program sym
        val class = (fn (Code_Thingol.Classparam c) => c) class_stmt
      in
        class
      end
    val lookup_method_class = lookup_method_class_gen program
      
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
      |> dedup
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
              then (mdl, dedup (import @ import'))
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

    (** Strip module prefix from resolved names (use short local names within a module). **)
    fun modify_deresolver deresolver sym = 
      let
        val sname = deresolver sym
        fun after_last_dot s =
          (case List.rev (String.fields (fn c => c = #".") s) of
              [] => s
            | x::_ => x)
      in
        after_last_dot sname
      end

    (** Print a single statement within its module context. **)
    fun print_stmt prefix_fragments (_, (export, stmt)) = (print_rust_stmt
      tyco_syntax const_syntax (make_vars reserved_syms)
      (Code_Thingol.is_constr program) (modify_deresolver (deresolver prefix_fragments))
      is_inf_typeco is_invdependent_typecos 
      lookup_constant_typeco lookup_constant_fun
      lookup_class_methods lookup_method_class)
      export stmt
      |> apfst (fn decl => if Code_Namespace.not_private export then SOME decl else NONE);

    (** Print a module: gather declarations, resolve imports, and wrap in module body. **)
    fun print_module _ base _ xs =
      let
        val (raw_decls, body) = split_list xs;
        val decls = maps these raw_decls
        val imports = filter (fn (sym, _) => (sym = base)) module_imports
          |> (fn mods => case mods of [(_, imports)] => imports | [] => []) 
      in (SOME [str base], print_rust_module base decls imports rust_includes body) end;

    (** Assemble final output: Cargo.toml + main.rs + per-module .rs files.
        Unused modules get empty placeholder files to pass compilation. **)
    val ps = Code_Namespace.print_hierarchical {
        print_module = print_module, print_stmt = print_stmt,
        lift_markup = K I } rust_program;
    val modules = map fst ps
      |> map (fn (SOME [x]) => (Pretty.string_of x))
    val unused_modules = lminus raw_modules modules
    val _ = tracing("mods="^(wrap_list raw_modules)^"  used="^(wrap_list modules)^"  unused="^(wrap_list unused_modules))
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
    renders as "impl Fn(A, B) -> C + Clone" in Rust. **)
fun fn_trait_impl_syntax print_typ fxy [ty1, ty2] =
  let
    val ts = extract_typ print_typ ("fun"`%%[ty1, ty2])
    val ret = List.last ts
    val params = List.take (ts, ((List.length ts) - 1))
  in
    Pretty.block(
      str "impl Fn"
      :: enum "," "(" ")" params
      :: str " -> "
      :: ret
      :: [str " + Clone"]
    )
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
