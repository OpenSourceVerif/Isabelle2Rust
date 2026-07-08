theory Semigroup_Test
  imports Main "Rust.Rust_Setup"
begin

(* Superclasses and polymorphic instances share the same semigroup family. *)

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

class monoid = semigroup +
  fixes zero :: "'a"

definition monoid_plus :: "'a::monoid \<Rightarrow> 'a \<Rightarrow> 'a" where
  "monoid_plus x y = plus x y"

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

fun zero_list :: "('a::monoid) list \<Rightarrow> 'a list" where
  "zero_list xs = map (\<lambda>_. zero) xs"

fun sum_Nat :: "Nat \<Rightarrow> Nat" where
  "sum_Nat x = x +s zero"

fun sum_list :: "('a::monoid) list \<Rightarrow> 'a" where
  "sum_list xs = fold plus xs zero"

datatype ('a, 'b) pair_box = PairBox 'a 'b

instantiation pair_box :: (semigroup, semigroup) semigroup
begin

fun plus_pair_box :: "('a::semigroup, 'b::semigroup) pair_box \<Rightarrow>
    ('a, 'b) pair_box \<Rightarrow> ('a, 'b) pair_box" where
  "PairBox x y +s PairBox x' y' = PairBox (x +s x') (y +s y')"

instance ..
end

instantiation pair_box :: (monoid, monoid) monoid
begin

definition zero_pair_box :: "('a::monoid, 'b::monoid) pair_box" where
  "zero = PairBox zero zero"

instance ..
end

fun sum_box :: "('a::monoid, 'b::monoid) pair_box \<Rightarrow> ('a, 'b) pair_box" where
  "sum_box x = x +s (zero :: ('a, 'b) pair_box)"

instantiation option :: (semigroup) semigroup
begin

fun plus_option :: "'a option \<Rightarrow> 'a option \<Rightarrow> 'a option" where
  "None +s None = None"
| "Some x +s None = Some x"
| "None +s Some x = Some x"
| "Some x +s Some y = Some (x +s y)"

instance ..
end

definition plus_none :: "'a::semigroup option \<Rightarrow> 'a option" where
  "plus_none x = x +s None"

export_code
  monoid_plus zero_list sum_Nat sum_list sum_box plus_none
  in Rust

end
