theory Tuple_Callback_Dictionary_Test
  imports Rust_Base_Setup
begin

text \<open>
  A polymorphic consumer passes a pair containing its type parameter to a
  callback. Instantiating that parameter with a binary HOL function selects the
  recursively unary Rust function representation required by its class
  dictionary. The callback's pair binder must use that same representation:
  wrapping an independently printed flat callback cannot convert the pair.
  Both the callback and the dictionary method invoke the supplied function,
  so successful compilation alone does not establish the required semantics.
\<close>

class tuple_sample =
  fixes tuple_sample :: 'a

instantiation bool :: tuple_sample
begin
definition tuple_sample_bool :: bool where "tuple_sample_bool = False"
instance ..
end

class tuple_observe =
  fixes tuple_observe :: "'a \<Rightarrow> bool"

instantiation bool :: tuple_observe
begin
definition tuple_observe_bool :: "bool \<Rightarrow> bool"
  where "tuple_observe_bool b = b"
instance ..
end

instantiation "fun" :: (tuple_sample, tuple_observe) tuple_observe
begin
definition tuple_observe_fun :: "('a \<Rightarrow> 'b) \<Rightarrow> bool"
  where "tuple_observe_fun f = tuple_observe (f tuple_sample)"
instance ..
end

definition consume_callback ::
  "('a::tuple_observe \<times> bool \<Rightarrow> bool) \<Rightarrow> 'a \<Rightarrow> bool"
  where "consume_callback k f = (k (f, True) \<and> tuple_observe f)"

definition observe_tuple_callback :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_tuple_callback f = consume_callback (\<lambda>(g, b). g False b) f"

lemma observation_values:
  "observe_tuple_callback (\<lambda>x y. \<not> x)"
  "\<not> observe_tuple_callback (\<lambda>x y. y)"
  "\<not> observe_tuple_callback (\<lambda>x y. \<not> y)"
  by (simp_all add: observe_tuple_callback_def consume_callback_def
      tuple_observe_fun_def tuple_observe_bool_def tuple_sample_bool_def)

text \<open>
  The same representation must survive destructuring a nominal one-constructor
  datatype and a list pattern crossing its recursive Box boundary.
\<close>

datatype 'a callback_box = CallbackBox 'a

definition consume_box_callback ::
  "('a::tuple_observe callback_box \<Rightarrow> bool) \<Rightarrow> 'a \<Rightarrow> bool"
  where "consume_box_callback k f = (k (CallbackBox f) \<and> tuple_observe f)"

definition observe_box_callback :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_box_callback f =
    consume_box_callback (\<lambda>box. case box of CallbackBox g \<Rightarrow> g False True) f"

definition consume_list_callback ::
  "(('a::tuple_observe \<times> bool) list \<Rightarrow> bool) \<Rightarrow> 'a \<Rightarrow> bool"
  where "consume_list_callback k f =
    (k [(f, False), (f, True)] \<and> tuple_observe f)"

definition observe_list_callback :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "observe_list_callback f =
    consume_list_callback
      (\<lambda>xs. case xs of [(h, a), (g, b)] \<Rightarrow> g False b | _ \<Rightarrow> False) f"

lemma container_observation_values:
  "observe_box_callback (\<lambda>x y. \<not> x)"
  "\<not> observe_box_callback (\<lambda>x y. y)"
  "\<not> observe_box_callback (\<lambda>x y. \<not> y)"
  "observe_list_callback (\<lambda>x y. \<not> x)"
  "\<not> observe_list_callback (\<lambda>x y. y)"
  "\<not> observe_list_callback (\<lambda>x y. \<not> y)"
  by (simp_all add: observe_box_callback_def consume_box_callback_def
      observe_list_callback_def consume_list_callback_def
      tuple_observe_fun_def tuple_observe_bool_def tuple_sample_bool_def)

export_code observe_tuple_callback observe_box_callback observe_list_callback
  in Rust module_name TupleCallbackDictionary

end
