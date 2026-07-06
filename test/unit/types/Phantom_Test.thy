theory Phantom_Test
  imports Main "Rust.Rust_Setup"
begin

(* Multiple and nullary phantom parameters. *)
datatype ('a, 'b) tagged2 = T2 int
datatype 'a marker = MkMarker

definition mk2 :: "int \<Rightarrow> ('a, 'b) tagged2" where
  "mk2 n = T2 n"

definition get2 :: "('a, 'b) tagged2 \<Rightarrow> int" where
  "get2 x = (case x of T2 n \<Rightarrow> n)"

definition mk_marker :: "'a marker" where
  "mk_marker = MkMarker"

definition marker_seen :: "'a marker \<Rightarrow> bool" where
  "marker_seen x = (case x of MkMarker \<Rightarrow> True)"

(* Single and partial phantom parameters. *)
datatype 'a tagged = Tagged int
datatype ('a, 'b) partial_tagged = PartialTagged 'a

definition mk_tag :: "int \<Rightarrow> 'a tagged" where
  "mk_tag n = Tagged n"

definition untag :: "'a tagged \<Rightarrow> int" where
  "untag x = (case x of Tagged n \<Rightarrow> n)"

definition mk_partial :: "'a \<Rightarrow> ('a, 'b) partial_tagged" where
  "mk_partial x = PartialTagged x"

definition get_partial :: "('a, 'b) partial_tagged \<Rightarrow> 'a" where
  "get_partial x = (case x of PartialTagged v \<Rightarrow> v)"

export_code
  mk2 get2 mk_marker marker_seen mk_tag untag mk_partial get_partial
  in Rust

end
