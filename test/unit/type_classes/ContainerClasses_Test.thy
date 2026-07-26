theory ContainerClasses_Test
  imports Main "Rust.Rust_Base_Setup"
begin

class weightable =
  fixes weight_of :: "'a \<Rightarrow> nat"

instantiation bool :: weightable
begin

definition weight_of_bool :: "bool \<Rightarrow> nat" where
  "weight_of b = (if b then 1 else 0)"

instance ..
end

instantiation option :: (weightable) weightable
begin

fun weight_of_option :: "'a::weightable option \<Rightarrow> nat" where
  "weight_of None = 0"
| "weight_of (Some x) = weight_of x"

instance ..
end

instantiation list :: (weightable) weightable
begin

fun weight_of_list :: "'a::weightable list \<Rightarrow> nat" where
  "weight_of [] = 0"
| "weight_of (x # xs) = weight_of x + weight_of xs"

instance ..
end

instantiation prod :: (weightable, weightable) weightable
begin

definition weight_of_prod :: "('a::weightable \<times> 'b::weightable) \<Rightarrow> nat" where
  "weight_of p = weight_of (fst p) + weight_of (snd p)"

instance ..
end

datatype 'a class_tree =
    CTLeaf 'a
  | CTNode "'a class_tree" "'a class_tree"

instantiation class_tree :: (weightable) weightable
begin

fun weight_of_class_tree :: "'a::weightable class_tree \<Rightarrow> nat" where
  "weight_of (CTLeaf x) = weight_of x"
| "weight_of (CTNode l r) = weight_of l + weight_of r"

instance ..
end

datatype 'a class_box =
  ClassBox 'a

instantiation class_box :: (weightable) weightable
begin

fun weight_of_class_box :: "'a::weightable class_box \<Rightarrow> nat" where
  "weight_of (ClassBox x) = weight_of x"

instance ..
end

class flippable =
  fixes flip_value :: "'a \<Rightarrow> 'a"

instantiation bool :: flippable
begin

definition flip_value_bool :: "bool \<Rightarrow> bool" where
  "flip_value b = (\<not> b)"

instance ..
end

instantiation option :: (flippable) flippable
begin

fun flip_value_option :: "'a::flippable option \<Rightarrow> 'a option" where
  "flip_value None = None"
| "flip_value (Some x) = Some (flip_value x)"

instance ..
end

instantiation list :: (flippable) flippable
begin

fun flip_value_list :: "'a::flippable list \<Rightarrow> 'a list" where
  "flip_value [] = []"
| "flip_value (x # xs) = flip_value x # flip_value xs"

instance ..
end

instantiation prod :: (flippable, flippable) flippable
begin

definition flip_value_prod :: "('a::flippable \<times> 'b::flippable) \<Rightarrow> ('a \<times> 'b)" where
  "flip_value p = (flip_value (fst p), flip_value (snd p))"

instance ..
end

instantiation class_tree :: (flippable) flippable
begin

fun flip_value_class_tree :: "'a::flippable class_tree \<Rightarrow> 'a class_tree" where
  "flip_value (CTLeaf x) = CTLeaf (flip_value x)"
| "flip_value (CTNode l r) = CTNode (flip_value l) (flip_value r)"

instance ..
end

instantiation class_box :: (flippable) flippable
begin

fun flip_value_class_box :: "'a::flippable class_box \<Rightarrow> 'a class_box" where
  "flip_value (ClassBox x) = ClassBox (flip_value x)"

instance ..
end

(* Generic calls and concrete nested dispatch use the same class methods. *)

definition generic_weight :: "'a::weightable \<Rightarrow> nat" where
  "generic_weight x = weight_of x"

definition option_weight :: "bool option \<Rightarrow> nat" where
  "option_weight x = weight_of x"

definition list_weight :: "bool list \<Rightarrow> nat" where
  "list_weight xs = weight_of xs"

definition nested_list_weight :: "bool list list \<Rightarrow> nat" where
  "nested_list_weight xs = weight_of xs"

definition pair_weight :: "bool \<times> bool list \<Rightarrow> nat" where
  "pair_weight p = weight_of p"

definition tree_weight :: "bool class_tree \<Rightarrow> nat" where
  "tree_weight t = weight_of t"

definition nested_tree_weight :: "bool class_tree list \<Rightarrow> nat" where
  "nested_tree_weight ts = weight_of ts"

definition box_weight :: "bool list class_box \<Rightarrow> nat" where
  "box_weight b = weight_of b"

definition generic_flip :: "'a::flippable \<Rightarrow> 'a" where
  "generic_flip x = flip_value x"

definition flip_twice :: "'a::flippable \<Rightarrow> 'a" where
  "flip_twice x = flip_value (flip_value x)"

definition option_flip :: "bool option \<Rightarrow> bool option" where
  "option_flip x = flip_value x"

definition list_flip :: "bool list \<Rightarrow> bool list" where
  "list_flip xs = flip_value xs"

definition nested_list_flip :: "bool list list \<Rightarrow> bool list list" where
  "nested_list_flip xs = flip_value xs"

definition pair_flip :: "bool \<times> bool list \<Rightarrow> bool \<times> bool list" where
  "pair_flip p = flip_value p"

definition tree_flip :: "bool class_tree \<Rightarrow> bool class_tree" where
  "tree_flip t = flip_value t"

definition nested_tree_flip :: "bool class_tree list \<Rightarrow> bool class_tree list" where
  "nested_tree_flip ts = flip_value ts"

definition box_flip :: "bool list class_box \<Rightarrow> bool list class_box" where
  "box_flip b = flip_value b"

definition flip_and_weight ::
  "'a::{flippable,weightable} \<Rightarrow> nat \<times> nat" where
  "flip_and_weight x = (weight_of x, weight_of (flip_value x))"

definition choose_flip :: "bool \<Rightarrow> 'a::flippable \<Rightarrow> 'a" where
  "choose_flip b x = (if b then flip_value x else x)"

definition tree_metrics ::
  "bool class_tree \<Rightarrow> nat \<times> nat" where
  "tree_metrics t = (weight_of t, weight_of (flip_value t))"

export_code
  generic_weight option_weight list_weight nested_list_weight pair_weight
  tree_weight nested_tree_weight box_weight generic_flip flip_twice option_flip
  list_flip nested_list_flip pair_flip tree_flip nested_tree_flip box_flip
  flip_and_weight choose_flip tree_metrics
  in Rust

end
