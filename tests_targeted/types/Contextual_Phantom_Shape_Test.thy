theory Contextual_Phantom_Shape_Test
  imports Rust_Base_Setup
begin

text \<open>
  Phantom witnesses carry the same contextual datatype parameter shapes as
  constructor paths. A class dictionary may select nested function groups even
  when the phantom parameter has no data-bearing field. Cover constructors,
  patterns, recursively unused parameters, and independent payload parameters.
\<close>

datatype 'a contextual_marker = ContextualMarker

definition consume_marker :: "'a::equal \<Rightarrow> 'a contextual_marker \<Rightarrow> bool"
  where "consume_marker value marker = HOL.equal value value"

definition observe_contextual_marker :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_contextual_marker f = consume_marker f ContextualMarker"

definition consume_marker_callback ::
  "('a contextual_marker \<Rightarrow> bool) \<Rightarrow> 'a::equal \<Rightarrow> bool"
  where "consume_marker_callback k f = (k ContextualMarker \<and> HOL.equal f f)"

definition observe_marker_pattern :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_marker_pattern f = consume_marker_callback (\<lambda>ContextualMarker. True) f"

datatype 'a contextual_chain = ContextualEnd | ContextualStep "'a contextual_chain"

definition consume_chain :: "'a::equal \<Rightarrow> 'a contextual_chain \<Rightarrow> bool"
  where "consume_chain f chain = HOL.equal f f"

definition observe_contextual_chain :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_contextual_chain f = consume_chain f (ContextualStep ContextualEnd)"

datatype ('a, 'b) marker_payload = MarkerPayload 'b

definition consume_payload :: "'a::equal \<Rightarrow> ('a, 'b) marker_payload \<Rightarrow> 'b"
  where "consume_payload f payload =
    (case payload of MarkerPayload value \<Rightarrow> if HOL.equal f f then value else value)"

definition observe_marker_payload ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_marker_payload f x y = consume_payload f (MarkerPayload f) x y"

definition default_marker :: "(bool \<Rightarrow> bool \<Rightarrow> bool) contextual_marker"
  where "default_marker = ContextualMarker"

lemma marker_observations:
  "observe_contextual_marker f"
  "observe_marker_pattern f"
  "observe_contextual_chain f"
  "observe_marker_payload f x y = f x y"
  by (simp_all add: observe_contextual_marker_def consume_marker_def
      observe_marker_pattern_def consume_marker_callback_def
      observe_contextual_chain_def consume_chain_def
      observe_marker_payload_def consume_payload_def equal_eq)

export_code observe_contextual_marker observe_marker_pattern observe_contextual_chain
  observe_marker_payload default_marker in Rust module_name ContextualPhantomShape

end
