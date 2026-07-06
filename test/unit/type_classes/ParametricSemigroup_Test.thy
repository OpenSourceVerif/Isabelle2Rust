theory ParametricSemigroup_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Semigroup_Nat3_Test"


class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"  (infixl "+s" 65)

class monoid = semigroup +
  fixes zero :: "'a"

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

export_code
  sum_Box
  in Rust

end
