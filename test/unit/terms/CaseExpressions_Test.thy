theory CaseExpressions_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Case_Bool_Test"


fun neg :: "bool \<Rightarrow> bool" where
  "neg b = (case b of True \<Rightarrow> False | False \<Rightarrow> True)"

subsection "From Case_Default_Test"


datatype color = Red | Green | Blue | Other nat

fun is_primary :: "color \<Rightarrow> bool" where
  "is_primary Red = True"
| "is_primary Green = True"
| "is_primary Blue = True"
| "is_primary _ = False"

subsection "From Case_Length1_Test"


fun length1 :: "'a list \<Rightarrow> bool" where
  "length1 xs = (case xs of [] \<Rightarrow> False | [x] \<Rightarrow> True | _ \<Rightarrow> False)" 

subsection "From Case_Length2_Test"


fun length2 :: "int list \<Rightarrow> int" where
  "length2 xs = (case xs of [] \<Rightarrow> 0 | [x] \<Rightarrow> x*3 | _ \<Rightarrow> 0)" 

subsection "From Case_Option_Test"


fun get_or_zero :: "int option \<Rightarrow> int" where
  "get_or_zero x = (case x of None \<Rightarrow> 0 | Some n \<Rightarrow> n)"

subsection "From Case_Poly_Test"



fun Id :: "'a \<Rightarrow> 'a" where
  "Id x = (case x of y \<Rightarrow> y)"

subsection "From Partial_Match_Test"


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

export_code
  neg is_primary length1 length2 get_or_zero Id head0 first_or_chain
  in Rust

end
