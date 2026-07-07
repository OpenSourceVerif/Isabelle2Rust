theory Curry_HO_Fold_Test
  imports Main "Rust.Rust_Setup"
begin

(* Curry/uncurry consistency, facet 1: a higher-order combinator whose callback
   is a MULTI-ARGUMENT function.

   HOL curries every function, so the callback here has type 'a => 'b => 'b.
   The Rust backend must agree on ONE representation for that value across three
   sites:

     - the parameter type of `myfold` (a function value: Rc<dyn Fn(..)>);
     - the application `f x (myfold f xs b)` inside `myfold` (a call of a
       two-argument function value);
     - the closure literal `%x a. x + a` passed at the call in `sum_list2`.

   Today the definition side prints uncurried Rust fns while call sites and
   closure literals still treat a two-or-more-argument function value as a
   curried chain (deref-call the intermediate closure; nested `move |x|`
   closures), so rustc rejects it with E0593 (closure is expected to take 2
   arguments, but it takes 1) / E0061 (wrong argument count) / E0308.  A correct
   printer must pick ONE calling convention for function VALUES and use it
   consistently at parameters, closures and calls. *)

fun myfold :: "('a \<Rightarrow> 'b \<Rightarrow> 'b) \<Rightarrow> 'a list \<Rightarrow> 'b \<Rightarrow> 'b" where
  "myfold f [] b = b"
| "myfold f (x # xs) b = f x (myfold f xs b)"

definition sum_list2 :: "nat list \<Rightarrow> nat" where
  "sum_list2 xs = myfold (\<lambda>x a. x + a) xs 0"

export_code myfold sum_list2 in Rust

end
