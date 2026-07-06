theory Tuple_Test
  imports Main "Rust.Rust_Setup"
begin

fun make_tuple3 :: "'a \<Rightarrow> 'b \<Rightarrow> 'c \<Rightarrow> 'a \<times> 'b \<times> 'c" where
  "make_tuple3 x y z = (x, y, z)"

fun rotate_tuple3 :: "'a \<times> 'b \<times> 'c \<Rightarrow> 'b \<times> 'c \<times> 'a" where
  "rotate_tuple3 (x, y, z) = (y, z, x)"

fun middle_tuple3 :: "'a \<times> 'b \<times> 'c \<Rightarrow> 'b" where
  "middle_tuple3 (_, y, _) = y"

fun assoc_left :: "'a \<times> ('b \<times> 'c) \<Rightarrow> ('a \<times> 'b) \<times> 'c" where
  "assoc_left (x, (y, z)) = ((x, y), z)"

fun flatten_tuple4 :: "('a \<times> 'b) \<times> ('c \<times> 'd) \<Rightarrow> 'a \<times> 'b \<times> 'c \<times> 'd" where
  "flatten_tuple4 ((a, b), (c, d)) = (a, b, c, d)"

fun map_tuple3 :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a \<times> 'a \<times> 'a \<Rightarrow> 'b \<times> 'b \<times> 'b" where
  "map_tuple3 f (x, y, z) = (f x, f y, f z)"

export_code
  make_tuple3 rotate_tuple3 middle_tuple3 assoc_left flatten_tuple4 map_tuple3
  in Rust

end
