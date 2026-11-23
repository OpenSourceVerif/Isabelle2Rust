theory Shared_Container_Chain_Test
  imports Rust_Base_Setup
begin

definition witness_branch :: "'a itself \<Rightarrow> 'a itself \<Rightarrow> 'a itself"
  where "witness_branch x y = x"

definition witness_chain :: "'a itself \<Rightarrow> 'a itself"
  where "witness_chain x = witness_branch x x"

text \<open>
  Retain the branch declaration for result-shape inference while a test-only
  derived target erases its unit witness syntax. The shared argument DAG then
  has bounded Rust output even at depth 80. Inference must not expand its
  exponentially many unfolded paths. Ordinary exports below use the normal
  witness representation and have runtime checks.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val branch = Code_Symbol.Constant \<^const_name>\<open>witness_branch\<close>;
  val root = Code_Symbol.Constant \<^const_name>\<open>witness_chain\<close>;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>witness_chain\<close>];
  val branch_node = Code_Symbol.Graph.get_node base branch;
  fun restore program = program
    |> Code_Symbol.Graph.new_node (branch, branch_node)
    |> Code_Symbol.Graph.add_edge (root, branch);
  val target = "RustSharedContainerChain";
  val ctxt = Proof_Context.background_theory
    (Code_Target.add_derived_target (target, [("Rust", restore)])
      #> Code_Target.set_printings
        (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
          [(target, SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))]))
      #> Code_Target.set_printings
        (Code_Symbol.Constant (\<^const_name>\<open>witness_branch\<close>,
          [(target, SOME (Code_Printer.simple_const_syntax
            (2, fn _ => fn _ => fn _ => Pretty.str "()")))])))
    \<^context>;
  fun output depth =
    let
      fun replace (Code_Thingol.Fun ((scheme, [((pats, body), note)]), origin)) =
            let
              val (callee, args) = Code_Thingol.unfold_app body;
              val leaf = (case args of [x, y] =>
                  if x = y then x else error "expected repeated witness"
                | _ => error "expected binary witness branch");
              fun layer child = callee `$ child `$ child;
              val nested = funpow (depth + 1) layer leaf;
            in Code_Thingol.Fun
              ((scheme, [((pats, nested), note)]), origin) end
        | replace _ = error "expected one witness equation";
      val program = Code_Symbol.Graph.map_node root replace base;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for ctxt target "SharedContainerChain"
          NONE [] program false [root]))) ()
    end;
  val small = output 0;
  val start = Time.now ();
  val _ = List.app (fn depth =>
    if output depth = small then ()
    else error "shared container inference changed erased output") [8, 80, 0];
in
  val _ = writeln ("Shared container chain: depths 0/8/80/fresh passed in " ^
    Real.fmt (StringCvt.FIX (SOME 6)) (Time.toReal (Time.- (Time.now (), start))) ^
    " seconds");
end
\<close>

export_code witness_branch witness_chain in Rust module_name SharedContainerChain

end
