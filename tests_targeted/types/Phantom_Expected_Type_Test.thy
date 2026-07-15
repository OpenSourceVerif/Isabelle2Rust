theory Phantom_Expected_Type_Test
  imports Main "Rust.Rust_Setup"
begin

(* A phantom datatype constructor carries no ordinary field from which Rust can
   infer its type parameter.  Here the HOL annotation fixes the marker to the
   surrounding function's type variable 'a, but that connection is erased if
   the generated constructor contains only an untyped `PhantomData`.  The call
   to `consume_token` then introduces an unrelated unconstrained Rust generic
   and fails with E0283.  Construction must materialise the known HOL type as
   `PhantomData::<A>` so the callee receives `Token<A>` rather than `Token<_>`. *)
datatype 'a phantom_token = Token

definition consume_token :: "'a phantom_token \<Rightarrow> nat" where
  "consume_token _ = 0"

definition consume_outer_token :: "'a list \<Rightarrow> nat" where
  "consume_outer_token _ = consume_token (Token :: 'a phantom_token)"

export_code consume_outer_token in Rust

end
