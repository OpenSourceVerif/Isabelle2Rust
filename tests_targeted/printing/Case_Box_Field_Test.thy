theory Case_Box_Field_Test
  imports Rust_Base_Setup
begin

text \<open>
  A recursive constructor field contains a sum of a unit and a pair of trees.
  The existing Rust layout boxes that entire sum. A case expression in this
  field must therefore be boxed once after matching, regardless of whether it
  uses an ordinary match, nested matches through list Box fields, or a single
  irrefutable constructor binding. The instance method exercises the same field
  construction while its equations are printed inside a trait implementation.
\<close>

datatype box_case_tree =
    CaseLeaf bool
  | CaseBranch "unit + (box_case_tree \<times> box_case_tree)"

definition ordinary_case_field :: "bool option \<Rightarrow> box_case_tree" where
  "ordinary_case_field x =
    CaseBranch (case x of None \<Rightarrow> Inl ()
      | Some b \<Rightarrow> Inr (CaseLeaf b, CaseLeaf (\<not> b)))"

definition nested_case_field ::
  "bool option \<Rightarrow> bool option \<Rightarrow> box_case_tree" where
  "nested_case_field x y =
    CaseBranch (case x of None \<Rightarrow> Inl ()
      | Some a \<Rightarrow> (case y of None \<Rightarrow> Inr (CaseLeaf a, CaseLeaf a)
        | Some b \<Rightarrow> Inr (CaseLeaf a, CaseLeaf b)))"

definition staged_case_field :: "bool list \<Rightarrow> box_case_tree" where
  "staged_case_field xs =
    CaseBranch (case xs of [a, b] \<Rightarrow> Inr (CaseLeaf a, CaseLeaf b)
      | _ \<Rightarrow> Inl ())"

datatype case_pair = CasePair bool bool

definition irrefutable_case_field :: "case_pair \<Rightarrow> box_case_tree" where
  "irrefutable_case_field p =
    CaseBranch (case p of CasePair a b \<Rightarrow> Inr (CaseLeaf a, CaseLeaf b))"

class branch_merge =
  fixes merge_branch :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

instantiation box_case_tree :: branch_merge
begin

fun merge_branch_box_case_tree where
  "merge_branch_box_case_tree (CaseBranch x) (CaseBranch y) =
    CaseBranch (case x of Inl _ \<Rightarrow> y | Inr p \<Rightarrow> Inr p)"
| "merge_branch_box_case_tree (CaseLeaf a) y = CaseLeaf a"
| "merge_branch_box_case_tree (CaseBranch x) (CaseLeaf a) = CaseLeaf a"

instance ..

end

definition merge_branch_values :: "'a::branch_merge \<Rightarrow> 'a \<Rightarrow> 'a" where
  "merge_branch_values x y = merge_branch x y"

definition merge_case_fields :: "box_case_tree \<Rightarrow> box_case_tree \<Rightarrow> box_case_tree" where
  "merge_case_fields x y = merge_branch x y"

lemma ordinary_case_field_Some:
  "ordinary_case_field (Some b) = CaseBranch (Inr (CaseLeaf b, CaseLeaf (\<not> b)))"
  by (simp add: ordinary_case_field_def)

lemma staged_case_field_two:
  "staged_case_field [a,b] = CaseBranch (Inr (CaseLeaf a, CaseLeaf b))"
  by (simp add: staged_case_field_def)

export_code ordinary_case_field nested_case_field staged_case_field
  irrefutable_case_field merge_branch_values merge_case_fields
  in Rust module_name CaseBoxField

end
