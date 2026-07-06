theory Dispatch_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Inst_Mono_Dispatch_Test"


(* Regression test for H3 (D.3) false negative: a MONOMORPHIC instance of a
   non-`equal` class, dispatched to through a polymorphic function.

   `Nat :: semigroup` is monomorphic, so its projection function plus_Nat has an
   empty sort-context vs. The old reconstruction took candidate classes only from
   vs (plus an `equal`-name fallback), so a non-equal monomorphic instance was
   never reconstructed -> no `impl Semigroup for Nat` -> the polymorphic dispatch
   `dbl::<Nat>` fails to compile (Nat: Semigroup unsatisfied).

   Taking candidate classes from the whole program's class set (matched by the
   `<class>_<tyco>_inst` name) fixes it. *)

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

datatype Nat = Zero | Suc Nat

instantiation Nat :: semigroup
begin
fun plus_Nat :: "Nat \<Rightarrow> Nat \<Rightarrow> Nat" where
  "a +s Zero = a"
| "Zero +s a = a"
| "Suc a +s b = Suc (a +s b)"
instance ..
end

(* polymorphic dispatch through the class: dbl x = x +s x  ->  A::plus(x, x) *)
fun dbl :: "('a::semigroup) \<Rightarrow> 'a" where
  "dbl x = x +s x"

(* force the monomorphic Nat instance to be used via the trait *)
definition use_nat :: Nat where "use_nat = dbl (Suc Zero)"

export_code
  use_nat
  in Rust

end
