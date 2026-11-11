theory Produced_Container_Argument_Test
  imports Rust_Base_Setup
begin

text \<open>
  A fresh dictionary-selected container constrains the input of an enclosing
  polymorphic call. The outer map/image already exists in HOL; no existing
  container is rebuilt by the backend. Cover both a direct class method and
  an ordinary producer whose type parameter carries the same dictionary.
\<close>

definition selected_values :: "('a::enum \<Rightarrow> bool) \<Rightarrow> 'a list"
  where "selected_values p = filter p Enum.enum"

definition direct_values :: "bool list"
  where "direct_values =
    map (\<lambda>f. f True False) (Enum.enum :: (bool \<Rightarrow> bool \<Rightarrow> bool) list)"

definition ordinary_values :: "bool \<Rightarrow> bool list"
  where "ordinary_values b =
    map (\<lambda>f. f True False)
      (selected_values (\<lambda>f :: bool \<Rightarrow> bool \<Rightarrow> bool. f False True = b))"

definition collected_values :: "bool \<Rightarrow> bool set"
  where "collected_values b =
    image (\<lambda>f. f True False) {f :: bool \<Rightarrow> bool \<Rightarrow> bool. f False True = b}"

definition intersected_values :: "bool \<Rightarrow> bool set"
  where "intersected_values b =
    image (\<lambda>f. f True False)
      ({f :: bool \<Rightarrow> bool \<Rightarrow> bool. f False True = b} \<inter>
       {f. f True True = b})"

definition tuple_values :: "bool \<Rightarrow> bool set"
  where "tuple_values b =
    image (\<lambda>(f,g). f False False = g True True)
      (vimage (\<lambda>(f,g). f True False \<and> g False True) {b} ::
        ((bool \<Rightarrow> bool \<Rightarrow> bool) \<times>
         (bool \<Rightarrow> bool \<Rightarrow> bool)) set)"

lemma direct_observations:
  "length direct_values = 16"
  "length (filter id direct_values) = 8"
  by (eval)+

lemma ordinary_observations:
  "length (ordinary_values False) = 8"
  "length (ordinary_values True) = 8"
  "length (filter id (ordinary_values False)) = 4"
  "length (filter id (ordinary_values True)) = 4"
  by (eval)+

lemma collected_observations:
  "collected_values False = {False, True}"
  "collected_values True = {False, True}"
  "intersected_values False = {False, True}"
  "intersected_values True = {False, True}"
  "tuple_values False = {False, True}"
  "tuple_values True = {False, True}"
  by (eval)+

export_code direct_values ordinary_values collected_values intersected_values tuple_values
  in Rust module_name ProducedContainerArgument

end
