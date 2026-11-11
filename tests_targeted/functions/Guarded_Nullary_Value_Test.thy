theory Guarded_Nullary_Value_Test
  imports Rust_Base_Setup
begin

text \<open>
  These nullary corecursive values already have a finite eager representation:
  recursive calls occur only inside a constructor's function field. Constructing
  one node allocates a closure; it does not evaluate the next node. This is the
  same representation as a parameterized corecursive function.
\<close>

codatatype 'a guarded_language =
  Guarded_Language (accepting: bool) (advance: "'a \<Rightarrow> 'a guarded_language")

primcorec rejecting_language :: "'a guarded_language" where
  "accepting rejecting_language = False"
| "advance rejecting_language = (\<lambda>_. rejecting_language)"

primcorec accepting_language :: "'a guarded_language" where
  "accepting accepting_language = True"
| "advance accepting_language = (\<lambda>_. accepting_language)"

primcorec alternating_language :: "bool \<Rightarrow> 'a guarded_language" where
  "accepting (alternating_language b) = b"
| "advance (alternating_language b) = (\<lambda>_. alternating_language (\<not> b))"

definition even_language :: "'a guarded_language"
  where "even_language = alternating_language True"
definition odd_language :: "'a guarded_language"
  where "odd_language = alternating_language False"

fun observe_language :: "'a list \<Rightarrow> 'a guarded_language \<Rightarrow> bool" where
  "observe_language [] l = accepting l"
| "observe_language (x # xs) l = observe_language xs (advance l x)"

lemma rejecting_observation: "\<not> observe_language xs rejecting_language"
  by (induction xs) simp_all
lemma accepting_observation: "observe_language xs accepting_language"
  by (induction xs) simp_all
lemma alternating_observation:
  "observe_language [a, b] even_language"
  "\<not> observe_language [a] even_language"
  by (simp_all add: even_language_def)

codatatype strict_tree =
  Strict_Tree (strict_label: bool) (strict_left: strict_tree) (strict_right: strict_tree)
primcorec strict_infinite :: strict_tree where
  "strict_label strict_infinite = False"
| "strict_left strict_infinite = strict_infinite"
| "strict_right strict_infinite = strict_infinite"

definition guarded_probe_value :: "bool guarded_language"
  where "guarded_probe_value = rejecting_language"
definition force_guarded_field :: "bool guarded_language \<Rightarrow> bool guarded_language"
  where "force_guarded_field l = advance l False"

text \<open>
  Synthetic Thingol equations check the rejection boundary without introducing
  inconsistent HOL code equations. A constructor passed to a consumer is not a
  returned lazy value: that consumer may immediately invoke the stored callback.
\<close>

ML \<open>
local
  open Basic_Code_Thingol;
  val self_sym = Code_Symbol.Constant \<^const_name>\<open>guarded_probe_value\<close>;
  val force_sym = Code_Symbol.Constant \<^const_name>\<open>force_guarded_field\<close>;
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
  val stored = constructor `$ no `$ next;
  val force = atom force_sym [ty] ty;
  val base = Code_Thingol.consts_program \<^context>
    [\<^const_name>\<open>guarded_probe_value\<close>, \<^const_name>\<open>force_guarded_field\<close>];
  fun produce body =
    let
      val program = base
        |> Code_Symbol.Graph.map_node self_sym (fn _ =>
            Code_Thingol.Fun ((([], ty), [(([], body), (NONE, true))]), NONE))
        |> Code_Symbol.Graph.add_edge (self_sym, self_sym)
        |> Code_Symbol.Graph.add_edge (self_sym, force_sym);
    in Code_Target.produce_code_for \<^context> "Rust" "GuardedBoundary"
      NONE [] program false [self_sym] end;
  val _ =
    (case Exn.capture (fn () => Code_Target.produce_code \<^context> false
        [\<^const_name>\<open>strict_infinite\<close>] "Rust" "StrictInfinite" NONE []) () of
      Exn.Exn (ERROR msg) =>
        if String.isPrefix "Rust target does not support self-referential nullary values:" msg
        then () else error ("strict infinite tree: " ^ msg)
    | _ => error "strict infinite tree must remain rejected");
  val _ = produce stored;
  val _ = produce (ICase {term = no, typ = bool_ty,
    clauses = [(no, stored), (IVar NONE, stored)], primitive = stored});
  fun rejected label body =
    (case Exn.capture (fn () => produce body) () of
      Exn.Exn (ERROR msg) =>
        if String.isPrefix "Rust target does not support self-referential nullary values:" msg
        then () else error ("guarded boundary " ^ label ^ ": " ^ msg)
    | _ => error ("guarded boundary wrongly accepted " ^ label));
  val _ = rejected "immediately applied callback" (next `$ no);
  val _ = rejected "stored callback forced by consumer" (force `$ stored);
  val _ = rejected "stored callback forced in a case scrutinee"
    (ICase {term = force `$ stored, typ = ty,
      clauses = [(IVar NONE, stored)], primitive = stored});
  (* The same physical constructor is visited once as a returned branch and
     again as a consumed argument. A context-insensitive seen set would miss the
     second branch's eager reference. *)
  val _ = rejected "shared returned/consumed constructor"
    (ICase {term = no, typ = bool_ty,
      clauses = [(no, stored), (IVar NONE, force `$ stored)], primitive = stored});
in
  val _ = writeln "Guarded nullary boundary: eager application/consumer/scrutinee/shared contexts rejected";
end
\<close>

export_code rejecting_language accepting_language even_language odd_language
  accepting advance observe_language
  in Rust module_name GuardedNullaryValue

end
