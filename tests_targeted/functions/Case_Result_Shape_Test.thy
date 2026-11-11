theory Case_Result_Shape_Test
  imports Tuple_Callback_Dictionary_Test
begin

text \<open>
  A producer constructs a fresh pair whose function component is selected by
  the result dictionary. Its input retains its recorded representation.
  Each case branch must receive the producer's expected result shape, including
  direct bindings, ordinary matches, and matches below recursive Box fields.
  No materialized container is converted: the source explicitly constructs
  the result pair after extracting its function value.
\<close>

definition observe_produced ::
  "('b \<Rightarrow> 'a::tuple_observe \<times> bool) \<Rightarrow> 'b \<Rightarrow> bool"
  where "observe_produced producer input =
    (case producer input of (g, flag) \<Rightarrow> tuple_observe g = flag)"

definition observe_case_binding ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_case_binding f flag =
    observe_produced (\<lambda>input. case input of (g, b) \<Rightarrow> (g, b)) (f, flag)"

definition observe_case_box ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_case_box f flag =
    observe_produced
      (\<lambda>input. case input of CallbackBox g \<Rightarrow> (g, flag)) (CallbackBox f)"

definition observe_case_option ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_case_option f flag =
    observe_produced
      (\<lambda>input. case input of None \<Rightarrow> (f, False) | Some g \<Rightarrow> (g, True))
      (if flag then Some f else None)"

definition observe_case_nested ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_case_nested f flag =
    observe_produced
      (\<lambda>input. case input of [Some g] \<Rightarrow> (g, True) | _ \<Rightarrow> (f, False))
      (if flag then [Some f] else [])"

lemma case_result_observations:
  "observe_case_binding f flag = (f False False = flag)"
  "observe_case_box f flag = (f False False = flag)"
  "observe_case_option f flag = (f False False = flag)"
  "observe_case_nested f flag = (f False False = flag)"
  by (simp_all add: observe_case_binding_def observe_case_option_def
      observe_case_nested_def observe_case_box_def observe_produced_def tuple_observe_fun_def
      tuple_sample_bool_def tuple_observe_bool_def split: if_splits)

export_code observe_case_binding observe_case_box observe_case_option observe_case_nested
  in Rust module_name CaseResultShape

end
