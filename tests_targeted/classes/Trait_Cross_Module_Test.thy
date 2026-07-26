theory Trait_Cross_Module_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Regression test for R1 (D.4 finish): cross-module trait-method dispatch with
   globs removed. The trait `sg` and its method are forced into a separate Rust
   module `ClsMod`; the polymorphic dispatch `combine x y` (-> A::combine, since
   the receiver is a type variable) lives in the theory module and is reached via
   `use_t`. For `A::combine` / the `impl sg for T` to resolve, `ClsMod`'s trait
   must be in scope. With glob imports removed, this now requires the explicit
   `use crate::ClsMod::Sg;` that R1 emits. *)

class sg = fixes combine :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

datatype T = A | B

instantiation T :: sg
begin
fun combine_T :: "T \<Rightarrow> T \<Rightarrow> T" where
  "combine_T A y = y"
| "combine_T B y = B"
instance ..
end

(* polymorphic dispatch through the class: receiver is a tyvar -> A::combine *)
fun foldpair :: "('a::sg) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "foldpair x y = combine x y"

definition use_t :: T where "use_t = foldpair A B"

code_identifier
  type_class sg \<rightharpoonup> (Rust) "ClsMod.sg"
| constant combine \<rightharpoonup> (Rust) "ClsMod.combine"

export_code use_t in Rust

end
