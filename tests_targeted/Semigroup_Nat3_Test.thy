theory Semigroup_Nat3_Test
  imports Main "Rust.Rust_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"  (infixl "+s" 65)

class monoid = semigroup +
  fixes zero :: "'a"

datatype Nat = Zero | Suc Nat

(* Instance of semigroup for Nat: define the class operation plus *)
instantiation Nat :: semigroup
begin

fun plus_Nat :: "Nat \<Rightarrow> Nat \<Rightarrow> Nat" where
  "plus_Nat a Zero = a"
| "plus_Nat Zero a = a"
| "plus_Nat (Suc a) b = Suc (plus_Nat a b)"

instance ..
end

(* Instance of monoid for Nat: define the class operation zero *)
instantiation Nat :: monoid
begin

definition zero :: "Nat" where
  "zero = Zero"

instance ..
end

(* A concrete folding sum on Nat that uses +s and zero *)
fun sum_Nat :: "Nat \<Rightarrow> Nat" where
  "sum_Nat xs = (+s) xs zero"

export_code sum_Nat in Rust
export_code sum_Nat in Haskell
export_code sum_Nat in OCaml

end