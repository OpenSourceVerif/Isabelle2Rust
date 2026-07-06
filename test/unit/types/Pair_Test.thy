theory Pair_Test
  imports Main "Rust.Rust_Setup"
begin

definition int_pair :: "int \<Rightarrow> int \<times> int" where
  "int_pair x = (x, x)"

fun make_pair :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b" where
  "make_pair x y = (x, y)"

fun pair_left :: "'a \<times> 'b \<Rightarrow> 'a" where
  "pair_left (x, _) = x"

fun pair_right :: "'a \<times> 'b \<Rightarrow> 'b" where
  "pair_right (_, y) = y"

fun swap_pair :: "'a \<times> 'b \<Rightarrow> 'b \<times> 'a" where
  "swap_pair (x, y) = (y, x)"

fun dup_pair :: "'a \<Rightarrow> 'a \<times> 'a" where
  "dup_pair x = (x, x)"

fun map_pair :: "('a \<Rightarrow> 'c) \<Rightarrow> ('b \<Rightarrow> 'd) \<Rightarrow> 'a \<times> 'b \<Rightarrow> 'c \<times> 'd" where
  "map_pair f g (x, y) = (f x, g y)"

export_code
  int_pair make_pair pair_left pair_right swap_pair dup_pair map_pair
  in Rust

end
