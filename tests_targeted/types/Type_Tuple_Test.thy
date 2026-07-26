theory Type_Tuple_Test
  imports Main "Rust.Rust_Base_Setup"
begin


(*  Basic tuple operations  *)

(* Swap components: exercises tuple pattern in both arg and return position *)
fun swap :: "'a \<times> 'b \<Rightarrow> 'b \<times> 'a" where
  "swap (x, y) = (y, x)"

(* Construct a pair from two separate arguments *)
fun make_pair :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b" where
  "make_pair x y = (x, y)"

(* Duplicate a value into both components *)
fun dup :: "'a \<Rightarrow> 'a \<times> 'a" where
  "dup x = (x, x)"


(*  Nested tuples  *)

(* Re-associate a right-nested triple into a left-nested triple *)
fun assoc_left :: "'a \<times> ('b \<times> 'c) \<Rightarrow> ('a \<times> 'b) \<times> 'c" where
  "assoc_left (x, (y, z)) = ((x, y), z)"

(* Flatten a nested pair of pairs into a 4-tuple *)
fun flatten4 :: "('a \<times> 'b) \<times> ('c \<times> 'd) \<Rightarrow> 'a \<times> 'b \<times> 'c \<times> 'd" where
  "flatten4 ((a, b), (c, d)) = (a, b, c, d)"


(*  Higher-order functions over tuples  *)

(* Apply a function to both components of a homogeneous pair *)
fun map_both :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a \<times> 'a \<Rightarrow> 'b \<times> 'b" where
  "map_both f (x, y) = (f x, f y)"

(* Apply two functions to the respective components *)
fun map_pair :: "('a \<Rightarrow> 'c) \<Rightarrow> ('b \<Rightarrow> 'd) \<Rightarrow> 'a \<times> 'b \<Rightarrow> 'c \<times> 'd" where
  "map_pair f g (x, y) = (f x, g y)"

(* Uncurry: turn a two-argument function into one that takes a pair *)
fun uncurry :: "('a \<Rightarrow> 'b \<Rightarrow> 'c) \<Rightarrow> 'a \<times> 'b \<Rightarrow> 'c" where
  "uncurry f (x, y) = f x y"


export_code
  swap make_pair dup
  assoc_left flatten4
  map_both map_pair uncurry
  in Rust

end
