theory Polynomial_Instance_Bounds_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* hol-stress guidance test (Generate.thy: Polynomial.rs -- E0277 missing
   `A: Equal` on reconstructed EuclideanSemiring/UniqueEuclideanSemiring impls).

   The polynomial `Modulo` impl acquires a generated `A: Equal` bound because
   its executable equation compares coefficients, while the derived
   `EuclideanSemiring` impl is emitted with only `A: Field`.  Since the Rust
   Euclidean trait extends the modulo trait, its impl does not satisfy its own
   superclass requirement.

   This minimal analogue uses HOL equality in the base-class method.  Equality
   has no Isabelle sort constraint, but executable Rust equality adds the hidden
   `A: Equal` bound to `ModuloLike for PolyLike<A>`.  The method-bearing derived
   instance must propagate that bound to `EuclideanLike for PolyLike<A>`, just as
   the real polynomial instances must. *)

class modulo_like =
  fixes modulo_test :: "'a \<Rightarrow> bool"

class euclidean_like = modulo_like +
  fixes size_like :: "'a \<Rightarrow> nat"

datatype 'a poly_like = PolyLike 'a 'a

instantiation poly_like :: (type) modulo_like
begin

definition modulo_test_poly_like :: "'a poly_like \<Rightarrow> bool" where
  "modulo_test_poly_like p = (case p of PolyLike x y \<Rightarrow> x = y)"

instance ..

end


instantiation poly_like :: (type) euclidean_like
begin

definition size_like_poly_like :: "'a poly_like \<Rightarrow> nat" where
  "size_like_poly_like _ = 0"

instance ..

end


definition dispatch_size_like :: "'a::euclidean_like \<Rightarrow> nat" where
  "dispatch_size_like p = size_like p"

definition use_size_like :: "'a poly_like \<Rightarrow> nat" where
  "use_size_like p = dispatch_size_like p"

export_code dispatch_size_like use_size_like in Rust

end
