theory Phantom_Multi_Test
  imports Main "Rust.Rust_Setup"
begin

(* Regression for the PhantomData feature beyond the single-param case:
   - tagged2 has TWO phantom params ('a, 'b), exercising multiple PhantomData
     markers in declaration, construction and pattern.
   - marker has a phantom param on a NULLARY-payload constructor (MkMarker),
     exercising the zero-field-with-phantom branch (which must now emit parens). *)

datatype ('a, 'b) tagged2 = T2 int
datatype 'a marker = MkMarker

definition mk2 :: "int \<Rightarrow> ('a, 'b) tagged2" where
  "mk2 n = T2 n"

definition get2 :: "('a, 'b) tagged2 \<Rightarrow> int" where
  "get2 x = (case x of T2 n \<Rightarrow> n)"

definition mk_marker :: "'a marker" where
  "mk_marker = MkMarker"

export_code mk2 get2 mk_marker in Rust

end
