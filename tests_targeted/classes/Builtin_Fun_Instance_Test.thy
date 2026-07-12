theory Builtin_Fun_Instance_Test
  imports Main "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: Orderings.rs, Lattices.rs and
   Complete_Lattices.rs -- E0050 for pointwise instances on FUNCTION).

   HOL's built-in order and lattice classes instantiate the function type by
   equations such as `bot = (\<lambda>_. bot)`, `inf f g = (\<lambda>x. inf (f x)
   (g x))`, and `Inf A = (\<lambda>x. Inf (image (\<lambda>f. f x) A))`.  The Rust
   trait methods still take only the class parameter's arguments: zero for
   `bot`, two for binary `inf`, and one for complete `Inf`.  The backend must
   keep the function-domain binder inside the returned `Rc<dyn Fn>` value.

   In the broad export it instead appends that binder to each `impl fn`, e.g.
   `fn bot(x: A) -> B` for the zero-argument trait declaration and
   `fn inf(f, g, x) -> B` for the two-argument declaration.  These definitions
   force all three arities through the real HOL classes, complementing the
   custom-class Fun_Instance_Test, which already compiles. *)

definition pointwise_bot :: "nat \<Rightarrow> bool" where
  "pointwise_bot = bot"

definition pointwise_top :: "nat \<Rightarrow> bool" where
  "pointwise_top = top"

definition pointwise_inf :: "(nat \<Rightarrow> bool) \<Rightarrow> (nat \<Rightarrow> bool) \<Rightarrow> nat \<Rightarrow> bool" where
  "pointwise_inf f g = inf f g"

definition pointwise_Inf :: "(nat \<Rightarrow> bool) set \<Rightarrow> nat \<Rightarrow> bool" where
  "pointwise_Inf A = Inf A"

export_code pointwise_bot pointwise_top pointwise_inf pointwise_Inf in Rust

end
