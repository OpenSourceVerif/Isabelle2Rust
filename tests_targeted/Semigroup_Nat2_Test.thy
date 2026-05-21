theory Semigroup_Nat2_Test
  imports Main "Rust.Rust_Setup"
begin

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

(*class test =
  fixes minus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "-s" 65)*)

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

fun sum_Nat :: "Nat \<Rightarrow> Nat" where
  "sum_Nat xs = (+s) xs zero"

export_code sum_Nat in Rust

fun sum :: "('a :: monoid) list \<Rightarrow> 'a" where
  "sum xs = fold plus xs zero"

export_code sum in Rust


datatype ('a,'b)  Box = Box 'a 'b

instantiation Box :: (semigroup, semigroup) semigroup
begin

fun plus_Box :: "('a::semigroup,'b::semigroup) Box \<Rightarrow> ('a,'b) Box \<Rightarrow> ('a,'b) Box" where
  "Box x y +s Box x' y' = Box (x +s x') (y +s y')"

instance ..
end

instantiation Box :: (monoid, monoid) monoid
begin

definition zero_Box :: "('a::monoid, 'b::monoid) Box" where
  "zero = Box zero zero"

instance ..
end

fun sum_Box :: "('a::monoid, 'b::monoid) Box \<Rightarrow> ('a, 'b) Box" where
  "sum_Box xs = (+s) xs (zero :: ('a, 'b) Box)"

export_code sum_Box in Rust

end