theory Class_Test
  imports Main "Rust.Rust_Base_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

class monoid = semigroup +
  fixes zero :: 'a

datatype Nat = Zero | Suc Nat

instantiation Nat :: semigroup
begin

fun plus_Nat :: "Nat \<Rightarrow> Nat \<Rightarrow> Nat" where
  "a +s Zero = a"
| "Zero +s a = a"
| "Suc a +s b = Suc (a +s b)"

instance ..
end

instantiation Nat :: monoid
begin

definition zero_Nat :: Nat where
  "zero = Zero"

instance ..
end

fun sum_list :: "('a::monoid) list \<Rightarrow> 'a" where
  "sum_list xs = fold plus xs zero"

(* Keep the concrete instances reachable in the generated test crate. *)
definition sum_Nat :: Nat where
  "sum_Nat = sum_list [Zero]"

export_code sum_Nat sum_list in Rust
export_code sum_Nat sum_list in OCaml


end
