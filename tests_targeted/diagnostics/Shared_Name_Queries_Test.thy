theory Shared_Name_Queries_Test
  imports Rust_Base_Setup
begin

text \<open>
  Name reservation and free-variable queries must retain the original ordering
  and binding rules without expanding shared Thingol branches as a tree.
  Code.abort's delayed argument provides a full-serializer control: its Rust
  output omits that argument, so a large shared fallback has the same output as
  a small equivalent fallback. The first ML block uses only established APIs
  and must also expose the traversal failure on the old backend.
\<close>

definition ignored_fallback :: "String.literal \<Rightarrow> bool" where
  "ignored_fallback msg = Code.abort msg (\<lambda>_. False)"

definition shared_name_capture :: "bool \<Rightarrow> (bool \<Rightarrow> bool) option" where
  "shared_name_capture x = Some (\<lambda>y. if y then x else \<not> x)"

ML \<open>
local
  open Basic_Code_Thingol;
  val sym = Code_Symbol.Constant \<^const_name>\<open>ignored_fallback\<close>;
  val ty = \<^type_name>\<open>bool\<close> `%% [];
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  val yes = atom \<^const_name>\<open>True\<close>;
  val no = atom \<^const_name>\<open>False\<close>;
  fun layer body = ICase {term = no, typ = ty,
    clauses = [(yes, body), (no, body)], primitive = no};
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>ignored_fallback\<close>];
  fun output depth =
    let
      val shared = funpow depth layer no;
      fun replace (Code_Thingol.Fun ((scheme, [((pats, body), annotation)]), origin)) =
            let
              val (callee, args) = Code_Thingol.unfold_app body;
              val fallback = (case nth args 1 of
                  bind `|=> (_, result_ty) => bind `|=> (shared, result_ty)
                | _ => error "expected abort fallback lambda");
              val body' = callee `$ hd args `$ fallback;
            in Code_Thingol.Fun ((scheme, [((pats, body'), annotation)]), origin) end
        | replace _ = error "expected one fallback equation";
      val program = Code_Symbol.Graph.map_node sym replace base;
    in
      Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
        map (fn (path, bytes) => (path, Bytes.content bytes))
          (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedNameQueries"
            NONE [] program false [sym]))) ()
    end;
  val small = output 0;
  val large = output 80;
  val _ = if small = large andalso small = output 0 then ()
    else error "shared name queries changed serialized Rust";
in
  val _ = writeln "Shared name serializer: depth 0/80 Rust bytes equal, fresh export passed";
end
\<close>

text \<open>
  Compare both set queries against the upstream reference on small terms,
  including nonempty accumulator seeds. A shared child appears under different
  lambda and case binders: globally marking it as seen is incorrect for free
  variables. Cache its intrinsic free names and remove binders at each parent.
  Primitive-only names remain excluded, unlike the instance-bound collector.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val ty = ITyVar "a";
  fun atom name = IConst {sym = Code_Symbol.Constant name, typargs = [],
    dicts = [], dom = [], range = ty, annotation = NONE};
  val x = IVar (SOME "x");
  val y = IVar (SOME "y");
  val z = IVar (SOME "z");
  val blank = IVar NONE;
  val shared = x `$ y;
  val primitive_only = atom "primitive_only" `$ IVar (SOME "primitive_var");
  fun abs v body = (v, ty) `|=> (body, ty);
  fun cases scrutinee clauses = ICase {term = scrutinee, typ = ty,
    clauses = clauses, primitive = primitive_only};
  fun layer body = cases z [(blank, body), (atom "pattern", body)];
  val scope_cases = cases z [(x, shared), (y, shared)];
  val scope_lambdas = abs (SOME "x") shared `$ abs (SOME "y") shared;
  val samples =
    [blank, x, y, z, atom "leaf", shared,
     abs NONE shared, abs (SOME "x") shared,
     abs (SOME "x") (abs (SOME "y") shared),
     abs (SOME "x") shared `$ shared,
     scope_cases, scope_lambdas, scope_cases `$ scope_lambdas,
     cases shared [], cases x [(y, shared)],
     cases z [(x `$ y, shared), (blank, shared)],
     cases z [(abs (SOME "x") shared, shared)],
     (* Equal shallow prefixes must not merge different deeper names. *)
     funpow 4 layer x `$ funpow 4 layer y,
     funpow 4 layer (atom "left") `$ funpow 4 layer (atom "right"),
     layer (atom "leaf" `$ shared), funpow 6 layer (atom "leaf" `$ shared)];
  val checks = Unsynchronized.ref 0;
  fun check label b =
    (checks := !checks + 1;
     if b then () else error ("shared name queries: " ^ label));
  val symbol_seeds = [[], [Code_Symbol.Constant "seed"],
    [Code_Symbol.Constant "leaf", Code_Symbol.Constant "seed"]];
  val variable_seeds = [[], ["seed"], ["x", "seed"], ["y", "x"]];
  val _ = List.app (fn (i, term) =>
    (List.app (fn seed =>
      check ("constant reference " ^ string_of_int i)
        (Code_Rust.add_distinct_constsyms term seed =
          Code_Thingol.add_constsyms term seed)) symbol_seeds;
     List.app (fn seed =>
      check ("variable reference " ^ string_of_int i)
        (Code_Rust.add_distinct_varnames term seed =
          Code_Thingol.add_varnames term seed)) variable_seeds))
    (map_index I samples);
  val huge = funpow 80 layer (atom "leaf" `$ shared);
  val small = funpow 6 layer (atom "leaf" `$ shared);
  val _ = Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
    (List.app (fn seed =>
       check "shared constant graph"
         (Code_Rust.add_distinct_constsyms huge seed =
           Code_Thingol.add_constsyms small seed)) symbol_seeds;
     List.app (fn seed =>
       check "shared free-variable graph"
         (Code_Rust.add_distinct_varnames huge seed =
           Code_Thingol.add_varnames small seed)) variable_seeds)) ();
  val _ = check "different binders around a shared case body"
    (Code_Rust.add_distinct_varnames scope_cases [] = ["x", "y", "z"]);
  val _ = check "different binders around a shared lambda body"
    (Code_Rust.add_distinct_varnames scope_lambdas [] = ["x", "y"]);
in
  val _ = writeln ("Shared name queries: " ^ string_of_int (!checks) ^
    " reference/order/scope/depth-80 checks passed");
end
\<close>

export_code ignored_fallback shared_name_capture in Rust module_name SharedNameQueries

end
