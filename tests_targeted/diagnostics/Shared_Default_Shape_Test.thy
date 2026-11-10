theory Shared_Default_Shape_Test
  imports Rust_Base_Setup
begin

text \<open>
  An executable function's parameter context records both its HOL type and its
  default Rust shape, even when the parameter pattern is a wildcard. Building
  that shape must retain sharing in nested type arguments.

  The test-local itself printer ignores its single type argument. Missing and
  executable functions therefore have bounded output for the same deep shared
  signature. The missing function controls for signature queries, while the
  executable one additionally enters typed-pattern shape conversion.
\<close>

setup \<open>Code_Target.set_printings
  (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
    [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))\<close>

definition missing_witness :: "'a itself \<Rightarrow> bool" where
  "missing_witness _ = True"
declare missing_witness_def [code del]

definition witness_true :: "'a itself \<Rightarrow> bool" where
  "witness_true _ = True"

text \<open>
  Ordinary adjacent HOL arrows in a function argument form one flat Rust Fn
  group. This executable control must continue accepting a two-argument closure
  after the shared-type conversion is memoized.
\<close>

definition shape_apply :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool" where
  "shape_apply f x y = f x y"

ML \<open>
local
  open Basic_Code_Thingol;
  val missing = Code_Symbol.Constant \<^const_name>\<open>missing_witness\<close>;
  val live = Code_Symbol.Constant \<^const_name>\<open>witness_true\<close>;
  val missing_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>missing_witness\<close>];
  val live_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_true\<close>];
  val _ = (case Code_Symbol.Graph.get_node missing_program missing of
      Code_Thingol.Fun ((_, []), _) => ()
    | _ => error "expected missing witness equations");
  val _ = (case Code_Symbol.Graph.get_node live_program live of
      Code_Thingol.Fun ((_, [(([IVar _], _), _)]), _) => ()
    | _ => error "expected one executable witness parameter");
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
      val function_ty = arrow (\<^type_name>\<open>itself\<close> `%% [payload]) bool;
      fun replace (Code_Thingol.Fun ((_, eqs), origin)) =
            Code_Thingol.Fun (((map (rpair []) variables, function_ty), eqs), origin)
        | replace _ = error "expected function";
      val program' = Code_Symbol.Graph.map_node symbol replace program;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for \<^context> "Rust" "SharedDefaultShape"
          NONE [] program' false [symbol]))) ()
    end;
  val control = output missing_program missing ["a"] a;
  val _ = if control = output missing_program missing ["a"] (shared 80 a) then ()
    else error "missing-equation control changed output";
  val _ = writeln "Shared default shape: missing-equation depths 0/80 passed";
  fun live_output variables payload = output live_program live variables payload;
  val small = live_output ["a"] a;
  val _ = writeln "Shared default shape: executable depth zero passed";
  val start = Time.now ();
  val large = live_output ["a"] (shared 80 a);
  val middle = live_output ["a"] (shared 8 a);
  val fresh = live_output ["a"] a;
  val elapsed = Time.- (Time.now (), start);
  val _ = if small = large andalso small = middle andalso small = fresh then ()
    else error "shared default shape changed complete Rust output";
  val _ = writeln ("Shared default shape: executable depth 80/8/fresh passed in " ^
    Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds");
  val checks = Unsynchronized.ref 0;
  fun check label ok =
    (checks := !checks + 1;
     if ok then () else error ("shared default shape: " ^ label));
  val leaves = [pair a b, arrow a b, arrow a (arrow bool b),
    pair (arrow a b) (arrow b a), arrow (arrow a b) (arrow b a)];
  val _ = List.app (fn (i, leaf) =>
    check ("different child shapes " ^ string_of_int i)
      (live_output ["a", "b"] leaf = live_output ["a", "b"] (shared 80 leaf)))
    (map_index I leaves);
  val _ = check "closed shared type"
    (live_output [] bool = live_output [] (shared 80 bool));
  val _ = check "fresh conversion after other variable sets"
    (live_output ["a"] a = small);
in
  val _ = writeln ("Shared default shape: " ^ string_of_int (!checks) ^
    " function/container/closed/fresh-output checks passed");
end
\<close>

export_code missing_witness witness_true shape_apply
  in Rust module_name SharedDefaultShape

end
