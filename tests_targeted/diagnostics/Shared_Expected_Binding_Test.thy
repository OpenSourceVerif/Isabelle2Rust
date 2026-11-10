theory Shared_Expected_Binding_Test
  imports Rust_Base_Setup
begin

text \<open>
  In a nested polymorphic call, the outer argument supplies an expected result
  shape to the inner call. Binding that contextual shape to a shared declaration
  must not unfold every occurrence. A single call is the control for all the
  other matching and layout operations.

  The ML probe consistently retypes the declarations and every constant
  occurrence, and uses a context-local itself printer to keep output bounded.
  Ordinary export retains the standard Itself<A> representation. Independent
  renamed type graphs also exercise actual variable substitution.
\<close>

definition witness_identity :: "'a itself \<Rightarrow> 'a itself" where
  "witness_identity x = x"

definition witness_forward :: "'a itself \<Rightarrow> 'a itself" where
  "witness_forward x = witness_identity x"

definition witness_nested :: "'a itself \<Rightarrow> 'a itself" where
  "witness_nested x = witness_identity (witness_identity x)"

ML \<open>
local
  open Basic_Code_Thingol;
  val ctxt = Proof_Context.background_theory
    (Code_Target.set_printings
      (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
        [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))])))
    \<^context>;
  val identity = Code_Symbol.Constant \<^const_name>\<open>witness_identity\<close>;
  val forward = Code_Symbol.Constant \<^const_name>\<open>witness_forward\<close>;
  val nested = Code_Symbol.Constant \<^const_name>\<open>witness_nested\<close>;
  val nested_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_nested\<close>];
  val call_program = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_forward\<close>];
  val _ = (case Code_Symbol.Graph.get_node call_program forward of
      Code_Thingol.Fun ((_, [(([IVar (SOME x)],
          IConst {sym, annotation = NONE, ...} `$ IVar (SOME y)), _)]), _) =>
        if x = y andalso sym = identity then ()
        else error "expected an identity call on the wrapper parameter"
    | _ => error "expected one unannotated identity call");
  val _ = (case Code_Symbol.Graph.get_node nested_program nested of
      Code_Thingol.Fun ((_, [(([IVar (SOME x)],
          IConst {sym = outer, annotation = NONE, ...} `$
          (IConst {sym = inner, annotation = NONE, ...} `$ IVar (SOME y))), _)]), _) =>
        if x = y andalso outer = identity andalso inner = identity then ()
        else error "expected two nested identity calls"
    | _ => error "expected nested-call body");
  val a = ITyVar "a";
  val b = ITyVar "b";
  val bool = \<^type_name>\<open>bool\<close> `%% [];
  fun pair x y = \<^type_name>\<open>prod\<close> `%% [x, y];
  fun arrow x y = "fun" `%% [x, y];
  fun shared 0 leaf = leaf
    | shared n leaf =
        let val child = shared (n - 1) leaf in pair child child end;
  fun output_pair program roots variables payload caller_variables caller_payload =
    let
      val witness = \<^type_name>\<open>itself\<close> `%% [payload];
      val function_ty = arrow witness witness;
      val caller_witness = \<^type_name>\<open>itself\<close> `%% [caller_payload];
      val caller_ty = arrow caller_witness caller_witness;
      fun replace_body (IConst {sym, annotation, ...} `$ arg) =
            if sym = identity then
              IConst {sym = sym, typargs = map ITyVar caller_variables,
                dicts = map (K []) caller_variables,
                dom = [caller_witness], range = caller_witness,
                annotation = annotation} `$ replace_body arg
            else error "unexpected wrapper callee"
        | replace_body (t as IVar _) = t
        | replace_body _ = error "unexpected witness equation";
      fun replace variables function_ty (Code_Thingol.Fun ((_, eqs), origin)) =
            Code_Thingol.Fun (((map (rpair []) variables, function_ty),
              map (apfst (apsnd replace_body)) eqs), origin)
        | replace _ _ _ = error "expected function";
      val program' = program
        |> Code_Symbol.Graph.map_node identity (replace variables function_ty)
        |> fold (fn caller => Code_Symbol.Graph.map_node caller
             (replace caller_variables caller_ty)) roots;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for ctxt "Rust" "SharedExpectedBinding"
          NONE [] program' false roots))) ()
    end;
  fun output program roots variables payload =
    output_pair program roots variables payload variables payload;
  val direct = output call_program [forward] ["a"] a;
  val _ = if direct = output call_program [forward] ["a"] (shared 80 a) then ()
    else error "single-call control changed output";
  val _ = writeln "Shared expected binding: single-call depths 0/80 passed";
  fun emit variables payload = output nested_program [nested] variables payload;
  val small = emit ["a"] a;
  val _ = writeln "Shared expected binding: nested call depth zero passed";
  val start = Time.now ();
  val large = emit ["a"] (shared 80 a);
  val middle = emit ["a"] (shared 8 a);
  val fresh = emit ["a"] a;
  val elapsed = Time.- (Time.now (), start);
  val _ = if small = large andalso small = middle andalso small = fresh then ()
    else error "shared expected binding changed complete Rust output";
  val _ = writeln ("Shared expected binding: nested call depth 80/8/fresh passed in " ^
    Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal elapsed) ^ " seconds");
  val leaves = [pair a b, arrow a b, arrow a (arrow bool b),
    pair (arrow a b) (arrow b a), arrow (arrow a b) (arrow b a)];
  val _ = List.app (fn leaf =>
    if emit ["a", "b"] leaf = emit ["a", "b"] (shared 80 leaf) then ()
    else error "shared expected binding changed function/container output") leaves;
  val _ = if emit [] bool = emit [] (shared 80 bool)
      andalso emit ["a"] a = small then ()
    else error "shared expected binding changed closed/fresh output";
  val _ = writeln "Shared expected binding: seven function/container/closed/fresh-output checks passed";
  (* Build declaration and occurrence DAGs independently, with different
     variable names. This exercises substitution rather than only a -> a. *)
  val renamed_leaves = [pair (ITyVar "u") (ITyVar "v"),
    arrow (ITyVar "u") (ITyVar "v"),
    arrow (ITyVar "u") (arrow bool (ITyVar "v")),
    pair (arrow (ITyVar "u") (ITyVar "v")) (arrow (ITyVar "v") (ITyVar "u")),
    arrow (arrow (ITyVar "u") (ITyVar "v")) (arrow (ITyVar "v") (ITyVar "u"))];
  fun renamed depth leaf other =
    output_pair nested_program [nested] ["a", "b"] (shared depth leaf)
      ["u", "v"] (shared depth other);
  val _ = List.app (fn (leaf, other) =>
    if renamed 0 leaf other = renamed 80 leaf other then ()
    else error "shared expected binding changed renamed-call output")
    (ListPair.zip (leaves, renamed_leaves));
in
  val _ = writeln "Shared expected binding: five independently allocated renamed-call checks passed";
end
\<close>

export_code witness_identity witness_forward witness_nested in Rust module_name SharedExpectedBinding

end
