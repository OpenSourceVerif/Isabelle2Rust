theory Curry_Class_Method_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Curry/uncurry consistency, facet 2 -- REGRESSION GUARD (now passes after the
   "preserve uncurried trait method call arity" fix).

   The root cause behind the earlier hol-stress E0061 / E0614 wave (e.g.
   Quickcheck_Random's `random`): a class method whose instance equation is
   ETA-REDUCED -- it binds fewer patterns than the method type has arrows -- when
   that instance is BOTH reconstructed into an impl and called at the concrete
   type.

   `combine :: 'a => 'a => 'a` has arrow arity two.  The D instance is defined
   point-free, `combine x = (%_. x)`, i.e. ONE explicit pattern.  Using it
   polymorphically in `foldc` forces an `impl combine2 for D`; calling it at the
   concrete type in `run` references the same eta-reduced instance constant.

   The impl method is printed fully uncurried, `fn combine(x0, x1) -> D` (so the
   trait declaration and impl agree -- the earlier E0050 fix).  The bug was that
   the concrete call site split arguments at the equation's pattern count
   (wanted_fn = 1), emitting the curried `( *D::combine(d) )(d)` -- calling
   combine with one argument (E0061) and dereferencing the returned D (E0614),
   which on this input also tripped the rustc `Vec` ICE.

   The fix counts the remaining range arrows when printing class-parameter and
   reconstructed instance-method calls, so `run` now emits the uncurried
   `D::combine(d, d)`.  This test guards that: it must keep compiling, and the
   polymorphic dispatch in `foldc` must stay `A::combine(x, y)`.  See
   Curry_Cond_Function_Test for the remaining, distinct closure-arity facet. *)

class combine2 =
  fixes combine :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

datatype D = MkD nat

instantiation D :: combine2
begin

definition combine_D: "combine (x::D) = (\<lambda>_. x)"

instance ..

end

fun foldc :: "('a :: combine2) list \<Rightarrow> 'a \<Rightarrow> 'a" where
  "foldc [] a = a"
| "foldc (x # xs) a = combine x (foldc xs a)"

definition run :: "D \<Rightarrow> D" where
  "run d = combine d d"

export_code foldc run in Rust

end
