theory Record_Test
  imports Main "Rust.Rust_Setup"
begin

record point =
  Xcoord :: int
  Ycoord :: int

definition origin :: point where
  "origin = (| Xcoord = 0, Ycoord = 0 |)"

definition make_point :: "int \<Rightarrow> int \<Rightarrow> point" where
  "make_point x y = (| Xcoord = x, Ycoord = y |)"

definition get_x :: "point \<Rightarrow> int" where
  "get_x p = Xcoord p"

definition get_y :: "point \<Rightarrow> int" where
  "get_y p = Ycoord p"

definition point_pair :: "point \<Rightarrow> int \<times> int" where
  "point_pair p = (Xcoord p, Ycoord p)"

definition replace_x :: "point \<Rightarrow> int \<Rightarrow> point" where
  "replace_x p x = p(| Xcoord := x |)"

record 'a tagged_point =
  tag :: 'a
  point_value :: point

definition tag_of :: "'a tagged_point \<Rightarrow> 'a" where
  "tag_of p = tag p"

definition retag :: "'a tagged_point \<Rightarrow> 'b \<Rightarrow> 'b tagged_point" where
  "retag p x = (| tag = x, point_value = point_value p |)"

export_code
  origin make_point get_x get_y point_pair replace_x tag_of retag
  in Rust

end
