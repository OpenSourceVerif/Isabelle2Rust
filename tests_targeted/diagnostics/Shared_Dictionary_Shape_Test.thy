theory Shared_Dictionary_Shape_Test
  imports Rust_Base_Setup
begin

text \<open>
  Dictionary-selected argument shapes must preserve sharing independently of
  the set-like dictionary-variable collection. The identity's witness payload
  is erased by test-local type syntax, so expanding product evidence has no
  corresponding increase in Rust output. Rebuild both the type and evidence
  at each query to catch structural equality that unfolds independent DAGs.
\<close>

definition dictionary_identity :: "'a::equal itself \<Rightarrow> 'a itself" where
  "dictionary_identity x = x"

definition dictionary_forward :: "'a::equal itself \<Rightarrow> 'a itself" where
  "dictionary_forward x = dictionary_identity x"

ML \<open>
local
  open Basic_Code_Thingol;
  val ctxt = Proof_Context.background_theory
    (Code_Target.set_printings
      (Code_Symbol.Type_Constructor (\<^type_name>\<open>itself\<close>,
        [("Rust", SOME (1, fn _ => fn _ => fn _ => Pretty.str "()"))])))
    \<^context>;
  val identity = Code_Symbol.Constant \<^const_name>\<open>dictionary_identity\<close>;
  val forward = Code_Symbol.Constant \<^const_name>\<open>dictionary_forward\<close>;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>dictionary_forward\<close>];
  val eqclass = \<^class>\<open>equal\<close>;
  val prod = \<^type_name>\<open>prod\<close>;
  fun nested 0 = (ITyVar "a", Dict ([], Dict_Var
        {var = "a", index = 0, length = 1, class = eqclass, unique = true}))
    | nested n =
        let val (ty, evidence) = nested (n - 1) in
          (prod `%% [ty, ty], Dict ([], Dict_Const ((prod, eqclass),
            [(ty, [evidence]), (ty, [evidence])])))
        end;
  fun output depth =
    let
      val (payload, evidence) = nested depth;
      val witness = \<^type_name>\<open>itself\<close> `%% [payload];
      val function_ty = "fun" `%% [witness, witness];
      fun replace (Code_Thingol.Fun (((vs, _), [((pats, _), note)]), origin)) =
            let val argument = (case pats of [p as IVar _] => p
                | _ => error "expected one witness variable");
              val callee = IConst {sym = identity, typargs = [payload],
                dicts = [[evidence]], dom = [witness], range = witness,
                annotation = NONE};
            in Code_Thingol.Fun
              (((vs, function_ty), [((pats, callee `$ argument), note)]), origin) end
        | replace _ = error "expected one witness equation";
      val program = Code_Symbol.Graph.map_node forward replace base;
    in Timeout.apply_physical (Time.fromSeconds 5) (fn () =>
      map (fn (path, bytes) => (path, Bytes.content bytes))
        (#1 (Code_Target.produce_code_for ctxt "Rust" "SharedDictionaryShape"
          NONE [] program false [forward]))) ()
    end;
  val small = output 0;
  val _ = writeln "Shared dictionary shape: depth zero passed";
  val start = Time.now ();
  val _ = List.app (fn depth =>
    if output depth = small then ()
    else error "shared dictionary shape changed erased output") [8, 80, 0];
in
  val _ = writeln ("Shared dictionary shape: depths 0/8/80/fresh passed in " ^
    Time.toString (Time.- (Time.now (), start)) ^ " seconds");
end
\<close>

export_code dictionary_identity dictionary_forward
  in Rust module_name SharedDictionaryShape

end
