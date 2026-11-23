theory Conditional_Guarded_Value_Test
  imports Guarded_Nullary_Value_Test
begin

text \<open>
  Choosing a constructor's callback creates a closure; the recursive factory is
  called only when that callback is invoked. These ordinary code equations keep
  the condition outside the lambdas and must use the existing Rc representation.
\<close>

definition choose_left :: bool where "choose_left = True"
definition choose_right :: bool where "choose_right = False"

primcorec conditional_language :: "'a guarded_language" where
  "accepting conditional_language = True"
| "advance conditional_language =
    (if choose_left then (\<lambda>_. conditional_language)
     else (\<lambda>_. rejecting_language))"

primcorec conditional_stopping :: "'a guarded_language" where
  "accepting conditional_stopping = True"
| "advance conditional_stopping =
    (if choose_right then (\<lambda>_. conditional_stopping)
     else (\<lambda>_. rejecting_language))"

lemma conditional_language_observations:
  "observe_language xs conditional_language"
  by (induction xs) (simp_all add: choose_left_def)

lemma conditional_stopping_observations:
  "\<not> observe_language (x # xs) conditional_stopping"
  by (simp add: choose_right_def rejecting_observation)


text \<open>
  Keep case scrutinees and consumed callbacks eager, even when the same physical
  conditional node was already visited as a stored result. A deeply shared
  field expression checks that this extra context does not expand a DAG.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val self_sym = Code_Symbol.Constant \<^const_name>\<open>guarded_probe_value\<close>;
  val force_sym = Code_Symbol.Constant \<^const_name>\<open>force_guarded_field\<close>;
  val accepting_sym = Code_Symbol.Constant \<^const_name>\<open>accepting\<close>;
  val bool_ty = \<^type_name>\<open>bool\<close> `%% [];
  val ty = \<^type_name>\<open>guarded_language\<close> `%% [bool_ty];
  val fn_ty = "fun" `%% [bool_ty, ty];
  fun atom sym dom range = IConst {sym = sym, typargs = [], dicts = [],
    dom = dom, range = range, annotation = NONE};
  val no = atom (Code_Symbol.Constant \<^const_name>\<open>False\<close>) [] bool_ty;
  val self = atom self_sym [] ty;
  val next = (SOME "ignored", bool_ty) `|=> (self, ty);
  val constructor = IConst {
    sym = Code_Symbol.Constant \<^const_name>\<open>Guarded_Language\<close>,
    typargs = [bool_ty], dicts = [[]], dom = [bool_ty, fn_ty],
    range = ty, annotation = NONE};
  val force = atom force_sym [ty] ty;
  val accepting = IConst {sym = accepting_sym, typargs = [bool_ty], dicts = [[]],
    dom = [ty], range = bool_ty, annotation = NONE};
  fun choose scrutinee body =
    ICase {term = scrutinee, typ = bool_ty,
      clauses = [(no, body), (IVar NONE, body)], primitive = body};
  val conditional = choose no next;
  val stored = constructor `$ no `$ conditional;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>guarded_probe_value\<close>,
     \<^const_name>\<open>force_guarded_field\<close>, \<^const_name>\<open>accepting\<close>];
  fun produce body =
    let
      val program = base
        |> Code_Symbol.Graph.map_node self_sym (fn _ =>
            Code_Thingol.Fun ((([], ty), [(([], body), (NONE, true))]), NONE))
        |> Code_Symbol.Graph.add_edge (self_sym, self_sym)
        |> Code_Symbol.Graph.add_edge (self_sym, force_sym)
        |> Code_Symbol.Graph.add_edge (self_sym, accepting_sym);
    in Code_Target.produce_code_for \<^context> "Rust" "ConditionalGuardedBoundary"
      NONE [] program false [self_sym] end;
  fun bounded f = Timeout.apply_physical (Time.fromSeconds 5) f ();
  fun rejected label body =
    (case Exn.capture (fn () => bounded (fn () => produce body)) () of
      Exn.Exn (ERROR msg) =>
        if String.isPrefix "Rust target does not support self-referential nullary values:" msg
        then () else error ("conditional guarded boundary " ^ label ^ ": " ^ msg)
    | _ => error ("conditional guarded boundary wrongly accepted " ^ label));
  fun contents body = bounded (fn () =>
    map (fn (path, bytes) => (path, Bytes.content bytes)) (#1 (produce body)));
  val expected = contents stored;
  val _ = rejected "immediately applied conditional callback" (conditional `$ no);
  val _ = rejected "conditional callback forced by consumer" (force `$ stored);
  val _ = rejected "eager field condition"
    (constructor `$ no `$ choose (accepting `$ self) next);
  val _ = rejected "shared stored/consumed conditional"
    (ICase {term = no, typ = bool_ty,
      clauses = [(no, stored), (IVar NONE, conditional `$ no)],
      primitive = stored});
  val shared = funpow 80 (choose no) no;
  fun late_reference () = rejected "shared field depth 80 before a late reference"
    (constructor `$ shared `$ choose (accepting `$ self) next);
  val start = Time.now ();
  val _ = late_reference ();
  val _ = late_reference ();
  val elapsed = Time.- (Time.now (), start);
  val _ = if contents stored = expected then ()
    else error "conditional guarded boundary: fresh output changed after rejection";
in
  val _ = writeln ("Conditional guarded boundary: stored branches accepted; " ^
    "application/consumer/scrutinee/shared contexts rejected; two depth-80 scans: " ^
    Time.toString elapsed ^ "s");
end
\<close>

export_code conditional_language conditional_stopping accepting advance observe_language
  in Rust module_name ConditionalGuardedValue

end
