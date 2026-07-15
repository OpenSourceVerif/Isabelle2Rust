theory Predicate_Operational_Bounds_Test
  imports "HOL.Predicate" "HOL.Enum" "Rust.Rust_Setup"
begin

(* Predicate equality is executable through the predicate order: `HOL.equal P Q`
   calls both `P \<le> Q` and `Q \<le> P`.  The logical `pred :: equal` instance has
   only a `type` parameter, but the executable order equation enumerates values
   of that parameter and therefore reconstructs Rust's `Ord for Pred<A>` with an
   operational `A: Enum` bound.

   Every caller of that reconstructed order impl must inherit the same bound.
   This includes both the standalone recursive helper `contained` and the
   reconstructed `Equal for Pred<A>` method.  Omitting the called impl's
   operational bound leaves their generated headers at `A: Equal` and produces
   four E0277 errors when Rust type-checks the generic bodies. *)

definition boolean_predicate_equal ::
  "bool Predicate.pred \<Rightarrow> bool Predicate.pred \<Rightarrow> bool" where
  "boolean_predicate_equal p q \<longleftrightarrow> HOL.equal p q"

definition boolean_predicate_less_eq ::
  "bool Predicate.pred \<Rightarrow> bool Predicate.pred \<Rightarrow> bool" where
  "boolean_predicate_less_eq p q \<longleftrightarrow> p \<le> q"

definition boolean_predicate_less ::
  "bool Predicate.pred \<Rightarrow> bool Predicate.pred \<Rightarrow> bool" where
  "boolean_predicate_less p q \<longleftrightarrow> p < q"

definition dispatch_less_eq :: "'a::ord \<Rightarrow> 'a \<Rightarrow> bool" where
  "dispatch_less_eq x y \<longleftrightarrow> x \<le> y"

export_code boolean_predicate_equal boolean_predicate_less_eq
  boolean_predicate_less dispatch_less_eq in Rust

end
