theory Shared_Shape_Erasure_Test
  imports Rust_Base_Setup
begin

text \<open>
  Selected result shapes are erased back to HOL types and compared with the
  declared result before printing. Shared type arguments must remain compact
  through both erasure and equality, including independently allocated shapes
  for separate equations.

  The test-local itself printer erases its payload. Each injected signature
  gives the same witness type to the identity argument and result, so the
  unchanged variable body remains well typed and the complete output is bounded.
\<close>

setup \<open>Code_Target.set_printings
  (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
    [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))\<close>

definition witness_identity :: "'a itself \<Rightarrow> 'a itself" where
  "witness_identity x = x"

fun witness_branches :: "bool \<Rightarrow> 'a itself \<Rightarrow> 'a itself" where
  "witness_branches True x = x"
| "witness_branches False x = x"

ML \<open>
local
  open Basic_Code_Thingol;
  val identity = Code_Symbol.Constant \<^const_name>\<open>witness_identity\<close>;
  val branches = Code_Symbol.Constant \<^const_name>\<open>witness_branches\<close>;
  val identity_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_identity\<close>];
  val branches_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_branches\<close>];
  val _ = (case Code_Symbol.Graph.get_node identity_program identity of
      Code_Thingol.Fun ((_, [(([IVar (SOME x)], IVar (SOME y)), _)]), _) =>
        if x = y then () else error "expected identity variable body"
    | _ => error "expected one identity equation");
  val _ = (case Code_Symbol.Graph.get_node branches_program branches of
      Code_Thingol.Fun ((_, [_, _]), _) => ()
    | _ => error "expected two witness equations");
  val a = ITyVar "a";
  val b = ITyVar "b";
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  fun pair x y = \<^type_name>\<open>prod\<close> `%% [x, y];
  fun arrow x y = "fun" `%% [x, y];
  fun shared 0 leaf = leaf
    | shared n leaf =
        let val child = shared (n - 1) leaf in pair child child end;
  fun output program symbol variables payload =
    let
      val witness = \<^type_name>\<open>itself\<close> `%% [payload];
      val identity_ty = arrow witness witness;
      val function_ty = if symbol = branches then arrow bool identity_ty
        else identity_ty;
      fun replace (Code_Thingol.Fun ((_, eqs), origin)) =
            Code_Thingol.Fun (((map (rpair []) variables, function_ty), eqs), origin)
        | replace _ = error "expected function";
      val program' = Code_Symbol.Graph.map_node symbol replace program;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedShapeErasure"
          NONE [] program' false [symbol]))) ()
    end;
  fun exercise label program symbol =
    let
      fun emit variables payload = output program symbol variables payload;
      val small = emit ["a"] a;
      val _ = writeln ("Shared shape erasure: " ^ label ^ " depth zero passed");
      val start = Time.now ();
      val large = emit ["a"] (shared 80 a);
      val middle = emit ["a"] (shared 8 a);
      val fresh = emit ["a"] a;
      val elapsed = Time.- (Time.now (), start);
      val _ = if small = large andalso small = middle andalso small = fresh then ()
        else error "shared shape erasure changed complete Rust output";
      val _ = writeln ("Shared shape erasure: " ^ label ^
        " depth 80/8/fresh passed in " ^
        Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds");
      val leaves = [pair a b, arrow a b, arrow a (arrow bool b),
        pair (arrow a b) (arrow b a), arrow (arrow a b) (arrow b a)];
      val _ = List.app (fn leaf =>
        if emit ["a", "b"] leaf = emit ["a", "b"] (shared 80 leaf) then ()
        else error "shared shape erasure changed function/container output") leaves;
      val _ = if emit [] bool = emit [] (shared 80 bool)
          andalso emit ["a"] a = small then ()
        else error "shared shape erasure changed closed/fresh output";
    in writeln ("Shared shape erasure: " ^ label ^
      " seven function/container/closed/fresh-output checks passed") end;
in
  val _ = exercise "identity" identity_program identity;
  val _ = exercise "branches" branches_program branches;
end
\<close>

export_code witness_identity witness_branches
  in Rust module_name SharedShapeErasure

end
