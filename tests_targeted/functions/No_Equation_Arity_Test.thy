theory No_Equation_Arity_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* An uninterpreted HOL constant has no executable code equation, so the Rust
   backend represents it by a panic stub.  Unlike a polymorphic value such as
   `undefined :: 'a`, the arrows declared directly on this constant belong to
   the stub's Rust parameter list.  A call must therefore remain
   `opaque_choose(p, n)`; emitting a nullary `opaque_choose()` followed by an
   Rc-function call gives the stub the wrong arity and dereferences its Nat
   result as though it were a function value.  Two declared arrows exercise the
   complete ordinary-parameter prefix rather than only a unary special case. *)
consts opaque_choose :: "bool \<Rightarrow> nat \<Rightarrow> nat"
declare [[code abort: opaque_choose]]

definition apply_opaque_choose :: "bool \<Rightarrow> nat \<Rightarrow> nat"
where
  "apply_opaque_choose p n = opaque_choose p n"

export_code apply_opaque_choose in Rust

end
