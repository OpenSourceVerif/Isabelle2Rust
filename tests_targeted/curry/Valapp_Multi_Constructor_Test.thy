theory Valapp_Multi_Constructor_Test
  imports "HOL.Code_Evaluation" "Rust.Rust_Setup"
begin

(* Code_Evaluation.valapp applies one HOL argument together with its reflected
   term at a time.  A constructor with three fields is therefore supplied to
   three nested valapp calls as a unary function returning a unary function
   returning a unary function.  Rust normally erases adjacent HOL arrows into
   one multi-argument Fn trait object; at these polymorphic result boundaries it
   must instead preserve all three application layers.  Preserving only the
   first layer yields Fn(A) -> Fn(B, C), while the second valapp requires
   Fn(A) -> Fn(B) -> Fn(C), and rustc reports E0308. *)
datatype ('a, 'b, 'c) reflected_triple = Reflected_Triple 'a 'b 'c

context
  includes term_syntax
begin

definition valtermify_reflected_triple ::
  "('a::typerep \<times> (unit \<Rightarrow> term)) \<Rightarrow>
   ('b::typerep \<times> (unit \<Rightarrow> term)) \<Rightarrow>
   ('c::typerep \<times> (unit \<Rightarrow> term)) \<Rightarrow>
   (('a, 'b, 'c) reflected_triple \<times> (unit \<Rightarrow> term))"
where [code_unfold]:
  "valtermify_reflected_triple a b c =
    Code_Evaluation.valtermify Reflected_Triple {\<cdot>} a {\<cdot>} b {\<cdot>} c"

end

export_code valtermify_reflected_triple in Rust

end
