theory Lazy_Thunk_Box_Test
  imports Main "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: Predicate.rs, Lazy_Sequence.rs,
   Random_Sequence.rs, Random_Pred.rs -- E0308 "expected `Box<Rc<dyn Fn(Unit)
   -> ...>>`, found `Rc<{closure@...}>`").

   A recursive datatype with a THUNK field -- a recursive occurrence guarded by
   `unit \<Rightarrow> _` (the lazy-sequence / Predicate.Pred shape) -- exposes a
   disagreement between the two Box levels (cf. memory `box-analysis-two-levels`):

   * The TYPE declaration boxes the recursive field, so the constructor variant
     is declared as `LCons(A, Box<Rc<dyn Fn(Unit) -> Llist<A>>>)`.
   * The TERM printer, at the construction site, wraps the thunk only in
     `Rc::new(move |_| ..)` and does NOT add the matching `Box::new(..)`.

   Curried/boxed decl vs unboxed value => rustc E0308 (on this input rustc even
   ICEs during type-checking of `one_two`, matching the ICEs in the broad
   export). The fix must make the term-level Box decision for a function-typed
   recursive field agree with the type-declaration's Box decision. *)

datatype 'a llist = LNil | LCons 'a "unit \<Rightarrow> 'a llist"

definition one_two :: "nat llist" where
  "one_two = LCons 1 (\<lambda>_. LCons 2 (\<lambda>_. LNil))"

fun lhead :: "'a \<Rightarrow> 'a llist \<Rightarrow> 'a" where
  "lhead d LNil = d"
| "lhead _ (LCons x _) = x"

definition force_head :: "nat" where
  "force_head = lhead 0 one_two"

export_code one_two lhead force_head in Rust

end
