theory Curry_Cond_Function_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Curry/uncurry consistency, facet 3 (the dominant remaining hol-stress wave,
   E0593 "closure is expected to take N arguments, but it takes 1"): a function
   whose RESULT is a multi-argument function value that is built by control flow
   BETWEEN the argument binders.

   `build_binop :: bool => nat => nat => nat` binds one explicit argument `c` and
   returns a `nat => nat => nat`.  The type printer folds every remaining arrow
   of the result into ONE uncurried trait object, `Rc<dyn Fn(Nat, Nat) -> Nat>`.
   But the body is `%x. if c then (%y. ..) else (%y. ..)`: the two binders `x`
   and `y` are separated by the `if`, so they cannot be flattened into a single
   `move |x, y|` -- the backend emits the CURRIED value
   `move |x| { if c { move |y| .. } else { move |y| .. } }`, whose type is
   `Fn(Nat) -> Rc<dyn Fn(Nat) -> Nat>`.

   Curried value vs uncurried result type => rustc rejects it with E0593 (and the
   E0631 / E0308 variants when such a value is passed to a higher-order consumer).
   This is the same shape as BNF_Wellorder_Constructions / Lattice_Constructions
   in the broad export.  Contrast Curry_HO_Fold_Test, where the two binders ARE
   adjacent (`%x a. ..`) and correctly flatten to `move |a, b|`.

   The refactor must make a function VALUE's closure arity agree with the arity
   the `fun` type printer commits to -- e.g. by eta-collecting the leading
   binders regardless of intervening control flow, or by printing the result
   type curried to match a curried value. *)

fun build_binop :: "bool \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "build_binop c = (\<lambda>x. if c then (\<lambda>y. x + y) else (\<lambda>y. x * y))"

definition use_binop :: "nat" where
  "use_binop = build_binop True 3 4"

export_code build_binop use_binop in Rust

end
