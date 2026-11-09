theory ADS_List_Equations_Test
  imports Rust_BigInt_Setup Rust_ADS_List_Setup
begin

text \<open>
  ADS_Construction replaces Nil/Cons as executable list constructors with the
  isomorphic list_R1_to_list constructor. Exercise ordinary list construction,
  a constructor passed as a function, the inverse projection, and typerep's
  nested lists, together with the existing lifted merge_list operation.
  The generated Rust must preserve the order and contents of
  every list and the HOL type names and arguments in type representations.
\<close>

definition ads_empty :: "bool list" where "ads_empty = []"
definition ads_prepend :: "bool \<Rightarrow> bool list \<Rightarrow> bool list"
  where "ads_prepend x xs = x # xs"
definition ads_triple :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool list"
  where "ads_triple x y z = [x, y, z]"
definition ads_rep :: "bool list \<Rightarrow> bool list_R1.list_R1"
  where "ads_rep = list_R1.list_to_list_R1"
definition ads_wrap :: "bool list_R1.list_R1 \<Rightarrow> bool list"
  where "ads_wrap = list_R1.list_R1_to_list"
definition ads_type :: typerep
  where "ads_type = Typerep.typerep TYPE(bool list \<times> unit)"

definition ads_merge :: "bool list \<Rightarrow> bool list \<Rightarrow> bool list option"
  where "ads_merge = merge_list (\<lambda>x y. if x = y then Some x else None)"

lemma ads_roundtrip:
  "ads_wrap (ads_rep xs) = xs"
  by (simp add: ads_wrap_def ads_rep_def list_R1.R1_of_list)

export_code ads_empty ads_prepend ads_triple ads_rep ads_wrap ads_type ads_merge
  in Rust module_name ADSList

end
