theory Partial_Match_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* A PARTIAL HOL function: no equation for the empty list. HOL allows this (the
   value on [] is underspecified); Isabelle's code generator emits only the given
   clause. Rust `match` must be total, so the backend adds a catch-all
   `_ => panic!(..)` arm — both for term-level (ICase) matches and for the
   multi-/single-clause match a function definition compiles to. Without it the
   generated code fails E0004 (non-exhaustive patterns). *)

fun head0 :: "nat list \<Rightarrow> nat" where
  "head0 (x # xs) = x"

(* Also exercise a partial match in a non-tail position (term-level ICase). *)
definition first_or_chain :: "nat list \<Rightarrow> nat list \<Rightarrow> nat" where
  "first_or_chain xs ys = head0 (xs @ ys)"

export_code head0 first_or_chain in Rust

end
