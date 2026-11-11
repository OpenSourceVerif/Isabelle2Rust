theory Contextual_Nullary_Method_Test
  imports Rust_Base_Setup
begin

text \<open>
  Exporting a polymorphic bottom keeps the Bot trait live. The empty set used
  below insert must then select the same function layout as insert's Equal
  dictionary. This instantiates a fresh nullary result, not an existing set.
\<close>

definition generic_bottom :: "'a::bot"
  where "generic_bottom = bot"

definition relation_choices :: "(bool \<Rightarrow> bool \<Rightarrow> bool) set"
  where "relation_choices = {(\<lambda>x y. x \<and> y), (\<lambda>x y. x \<or> y)}"

definition relation_observations :: "bool \<Rightarrow> bool \<Rightarrow> bool set"
  where "relation_observations a b = image (\<lambda>r. r a b) relation_choices"

lemma relation_observations:
  "relation_observations False False = {False}"
  "relation_observations False True = {False, True}"
  "relation_observations True False = {False, True}"
  "relation_observations True True = {True}"
  by (eval)+

class empty_layers =
  fixes empty_layers :: "'a list"

instantiation list :: (type) empty_layers
begin
definition empty_layers_list :: "'a list list"
  where "empty_layers_list = [[]]"
instance ..
end

definition generic_layers :: "'a::empty_layers list"
  where "generic_layers = empty_layers"

definition layered_callbacks :: "(bool \<Rightarrow> bool \<Rightarrow> bool) list"
  where "layered_callbacks =
    remdups ((\<lambda>x y. x \<noteq> y) #
      concat (empty_layers :: (bool \<Rightarrow> bool \<Rightarrow> bool) list list))"

lemma layered_callbacks_value:
  "layered_callbacks = [(\<lambda>x y. x \<noteq> y)]"
  by (simp add: layered_callbacks_def empty_layers_list_def)

text \<open>
  A function instance's fixed unary Self boundary and its codomain dictionary
  still take precedence over a flat constructor-field expectation.
\<close>

datatype callback_box = Callback_Box "(bool \<Rightarrow> bool \<Rightarrow> bool)"

definition bottom_box :: callback_box
  where "bottom_box = Callback_Box bot"

definition observe_bottom_box :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_bottom_box a b =
    (case bottom_box of Callback_Box f \<Rightarrow> f a b)"

definition applied_bottom :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "applied_bottom a b = (bot :: bool \<Rightarrow> bool \<Rightarrow> bool) a b"

lemma bottom_observations:
  "\<not> observe_bottom_box a b"
  "\<not> applied_bottom a b"
  by (simp_all add: observe_bottom_box_def bottom_box_def applied_bottom_def bot_fun_def)

export_code generic_bottom generic_layers layered_callbacks bottom_box
  observe_bottom_box applied_bottom
  relation_choices relation_observations
  in Rust module_name ContextualNullaryMethod

text \<open>The same set construction also works without exporting Bot itself.\<close>

export_code relation_choices relation_observations
  in Rust module_name ContextualNullaryMethodStandalone

end
