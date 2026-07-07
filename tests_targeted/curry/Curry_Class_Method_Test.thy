theory Curry_Class_Method_Test
  imports Main "Rust.Rust_Setup"
begin

(* Curry/uncurry consistency, facet 2 (the root cause behind the hol-stress
   E0061 / E0614 wave, e.g. Quickcheck_Random's `random`): a class method whose
   instance equation is ETA-REDUCED -- it binds fewer patterns than the method
   type has arrows -- when that instance is BOTH reconstructed into an impl and
   called at the concrete type.

   `combine :: 'a => 'a => 'a` has arrow arity two.  The D instance is defined
   point-free, `combine x = (%_. x)`, i.e. ONE explicit pattern.  Using it
   polymorphically in `foldc` forces the backend to reconstruct an
   `impl combine2 for D`; calling it at the concrete type in `run` references the
   same eta-reduced instance constant.  Two places then disagree on the arity:

     - the impl method is printed fully uncurried, `fn combine(x0, x1) -> D`
       (so the trait declaration and impl agree -- the earlier E0050 fix);
     - the CALL SITE splits arguments at the instance equation's pattern count
       (wanted_fn = 1), emitting the curried `( *D::combine(d) )(d)` -- it calls
       combine with one argument and dereferences the result.

   The generated `run` is thus `( *D::combine(d) )(d)`: combine is called with one
   argument (the underlying E0061 -- combine takes 2) and the returned D is
   dereferenced (the underlying E0614 -- D is not a pointer).  On this input rustc
   does not even report those cleanly -- it hits the internal `Vec` panic (the
   same ICE seen across the hol-stress export) while lowering the malformed call.
   Meanwhile `foldc`'s polymorphic dispatch prints correctly as the uncurried
   `A::combine(x, y)`, so the defect is specifically the CONCRETE instance-method
   call site.

   The focused refactor must make the definition arity and the call-site split
   point ONE consistent notion for every function value -- plain functions,
   instance methods and closures alike. *)

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
