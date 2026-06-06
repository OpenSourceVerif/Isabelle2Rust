theory Semigroup_Nat_Test
  imports Main "Rust.Rust_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)


class monoid = semigroup +
  fixes zero :: "'a"


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

definition zero_Nat :: "Nat" where
  "zero = Zero"

instance ..
end

fun zerolist :: "('a :: monoid) list \<Rightarrow> 'a list" where
  "zerolist xs = map (\<lambda>x. zero) xs"

export_code zerolist in Rust

end