theory Tuples_Test
  imports Main "Rust.Rust_Setup"
begin

(* Product types and Pair constructors are printed as Rust tuple syntax. *)

definition pair_build :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b" where
  "pair_build x y = (x, y)"

definition pair_swap :: "'a \<times> 'b \<Rightarrow> 'b \<times> 'a" where
  "pair_swap p = (case p of (x, y) \<Rightarrow> (y, x))"

definition pair_assoc :: "('a \<times> 'b) \<times> 'c \<Rightarrow> 'a \<times> ('b \<times> 'c)" where
  "pair_assoc p = (case p of ((x, y), z) \<Rightarrow> (x, (y, z)))"

definition pair_first_default :: "'a \<times> nat \<Rightarrow> nat" where
  "pair_first_default p = (case p of (_, n) \<Rightarrow> n)"

export_code
  pair_build pair_swap pair_assoc pair_first_default
  in Rust

end
