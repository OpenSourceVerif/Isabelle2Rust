theory Constructed_Callback_Pair_Test
  imports Tuple_Callback_Dictionary_Test
begin

text \<open>
  The callback receives an existing pair whose function component already uses
  the dictionary-selected shape. A polymorphic apply must instantiate its
  argument variable from that pair. The newly constructed function/flag pair
  can then accept the selected shape and adapt the function while constructing
  its fixed-layout datatype. No existing container needs rebuilding.
\<close>

datatype captured_callback = CapturedCallback "bool \<Rightarrow> bool \<Rightarrow> bool"

definition apply_value_pair :: "('a \<Rightarrow> 'b) \<times> bool \<Rightarrow> 'a \<times> bool \<Rightarrow> 'b \<times> bool"
  where "apply_value_pair fx xb = (fst fx (fst xb), snd xb)"

definition observe_constructed_pair :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_constructed_pair f =
    consume_callback
      (\<lambda>input. case apply_value_pair (CapturedCallback, False) input of
        (CapturedCallback g, b) \<Rightarrow> g False b) f"

definition observe_direct_constructor :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_direct_constructor f =
    consume_callback
      (\<lambda>(g, b). case CapturedCallback g of CapturedCallback h \<Rightarrow> h False b) f"

definition observe_forwarded_pair :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_forwarded_pair f =
    consume_callback
      (\<lambda>input. let forwarded = apply_value_pair (id, False) input in
        case apply_value_pair (CapturedCallback, False) forwarded of
          (CapturedCallback g, b) \<Rightarrow> g False b) f"

definition pair_with_phantom :: "'a \<times> bool \<Rightarrow> ('a \<times> bool) \<times> 'b option"
  where "pair_with_phantom input = (input, None)"

definition observe_explicit_pair :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_explicit_pair f =
    consume_callback
      (\<lambda>input. case (pair_with_phantom input ::
          ((bool \<Rightarrow> bool \<Rightarrow> bool) \<times> bool) \<times> bool option) of
        (forwarded, marker) \<Rightarrow>
          (case apply_value_pair (CapturedCallback, False) forwarded of
            (CapturedCallback g, b) \<Rightarrow> g False b)) f"

lemma forwarded_pair_observation:
  "observe_forwarded_pair f = (f False True \<and> f False False)"
  "observe_explicit_pair f = (f False True \<and> f False False)"
  by (simp_all add: observe_forwarded_pair_def observe_explicit_pair_def
      apply_value_pair_def pair_with_phantom_def consume_callback_def tuple_observe_fun_def
      tuple_observe_bool_def tuple_sample_bool_def split: prod.splits captured_callback.splits)

lemma constructed_pair_observation:
  "observe_constructed_pair f = (f False True \<and> f False False)"
  "observe_direct_constructor f = (f False True \<and> f False False)"
  by (simp_all add: observe_constructed_pair_def observe_direct_constructor_def
      apply_value_pair_def consume_callback_def tuple_observe_fun_def
      tuple_observe_bool_def tuple_sample_bool_def split: prod.splits captured_callback.splits)

export_code observe_constructed_pair observe_direct_constructor
  observe_forwarded_pair observe_explicit_pair
  in Rust module_name ConstructedCallbackPair

end
