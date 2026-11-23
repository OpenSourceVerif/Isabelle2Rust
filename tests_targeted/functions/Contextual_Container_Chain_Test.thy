theory Contextual_Container_Chain_Test
  imports Rust_Base_Setup
begin

text \<open>
  A source image explicitly rebuilds pairs before equality selects the
  representation of their function field. An enclosing product and observation
  must preserve that selected container representation.
\<close>

definition chain_intersection ::
  "(bool \<times> (bool \<Rightarrow> bool \<Rightarrow> bool)) set \<Rightarrow> bool set"
  where "chain_intersection r =
    image (\<lambda>(k,f). k = f True False)
      (image (\<lambda>(k,f). (k,f)) r \<inter> UNIV)"

definition chain_product ::
  "(bool \<times> (bool \<Rightarrow> bool \<Rightarrow> bool)) set \<Rightarrow> bool set"
  where "chain_product r =
    image (\<lambda>((k,f),b). (k = f True False) = b)
      ((image (\<lambda>(k,f). (k,f)) r \<inter> UNIV) \<times> {False, True})"

definition chain_plain ::
  "(bool \<times> (bool \<Rightarrow> bool \<Rightarrow> bool)) set \<Rightarrow> bool set"
  where "chain_plain r = image (\<lambda>(k,f). k = f True False) r"

definition chain_forward :: "'a set \<Rightarrow> 'a set"
  where "chain_forward r = r"

definition chain_deep_8 ::
  "(bool \<times> (bool \<Rightarrow> bool \<Rightarrow> bool)) set \<Rightarrow> bool set"
  where "chain_deep_8 r =
    image (\<lambda>(k,f). k = f True False)
      (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (image (\<lambda>(k,f). (k,f)) r \<inter> UNIV)))))))))"

definition chain_deep_32 ::
  "(bool \<times> (bool \<Rightarrow> bool \<Rightarrow> bool)) set \<Rightarrow> bool set"
  where "chain_deep_32 r =
    image (\<lambda>(k,f). k = f True False)
      (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (chain_forward (image (\<lambda>(k,f). (k,f)) r \<inter> UNIV)))))))))))))))))))))))))))))))))"

lemma chain_intersection_value: "chain_intersection r = chain_plain r"
  by (simp add: chain_intersection_def chain_plain_def)

lemma chain_product_observations:
  "chain_product {} = {}"
  "chain_product {(False, (\<lambda>x y. x \<and> y))} = {False, True}"
  by (eval)+

lemma chain_depth_values:
  "chain_deep_8 r = chain_plain r"
  "chain_deep_32 r = chain_plain r"
  by (simp_all add: chain_deep_8_def chain_deep_32_def
      chain_forward_def chain_plain_def)

export_code chain_intersection chain_product chain_plain chain_deep_8 chain_deep_32
  in Rust module_name ContextualContainerChain

end
