theory Phantom_Param_Test
  imports Main "Rust.Rust_Setup"
begin

(* A datatype with a PHANTOM type parameter: 'a appears on the left but in no
   constructor argument (the payload is just an int).  Isabelle/HOL — like OCaml
   and Haskell — allows this freely.  Rust does NOT: an unused generic parameter
   is rejected with E0392 "type parameter is never used".

   The faithful translation is `enum Tagged<A> { Tagged (Int) }`, which fails to
   compile.  The fix must detect phantom parameters and emit a `PhantomData<A>`
   marker (this is the special-casing the OCaml/Haskell backends never need,
   because their languages accept phantom parameters as-is).

   This mirrors the `'a word` / `'a bit0` / `'a itself` machinery that blocks the
   bpf `step` export, but in isolation — no `len`/`take_bit`/closure baggage. *)

datatype 'a tagged = Tagged int

definition mk_tag :: "int \<Rightarrow> 'a tagged" where
  "mk_tag n = Tagged n"

definition untag :: "'a tagged \<Rightarrow> int" where
  "untag x = (case x of Tagged n \<Rightarrow> n)"

export_code mk_tag untag in Rust

end
