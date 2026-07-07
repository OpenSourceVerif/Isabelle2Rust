theory Fun_Instance_Test
  imports Main "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: Function_Algebras.rs,
   Function_Division.rs -- E0050 "method `one` has 1 parameter but the
   declaration in trait `One::one` has 0" / "method `plus` has 3 parameters but
   the declaration ... has 2").

   HOL instantiates the FUNCTION type `'a => 'b` in the arithmetic classes
   (`one = (\<lambda>_. one)`, `plus f g = (\<lambda>x. f x + g x)`, ...). The Rust
   backend reconstructs `impl One for Rc<dyn Fn(A)->B>` etc., but eta-expands the
   instance method by the FUNCTION type's extra arrow, so the impl gains a
   trailing `eta_arg: A` parameter that the trait declaration does not have:

       trait One  { fn one() -> Self; }              // 0 params
       impl  One for Rc<dyn Fn(A)->B> {
         fn one(eta_arg_0: A) -> B { .. }             // 1 param  => E0050

   The method signature of a `fun`-type instance must match the trait arity; the
   eta-expansion that aligns a value's closure arity must NOT leak into the
   `impl fn` signature.

   Uses a fresh single-parameter class so the reconstruction is isolated from
   HOL's numeric hierarchy. *)

class pt =
  fixes unit_pt :: "'a"                       (* nullary class parameter *)
    and comb :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"   (* binary class parameter *)

instantiation "fun" :: (type, pt) pt
begin

definition unit_pt_fun :: "'a \<Rightarrow> 'b" where
  "unit_pt_fun = (\<lambda>_. unit_pt)"

definition comb_fun :: "('a \<Rightarrow> 'b) \<Rightarrow> ('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "comb_fun f g = (\<lambda>x. comb (f x) (g x))"

instance ..

end

definition use_unit :: "nat \<Rightarrow> ('a::pt)" where
  "use_unit = unit_pt"

definition use_comb :: "(nat \<Rightarrow> 'a::pt) \<Rightarrow> (nat \<Rightarrow> 'a) \<Rightarrow> nat \<Rightarrow> 'a" where
  "use_comb f g = comb f g"

export_code use_unit use_comb in Rust

end
