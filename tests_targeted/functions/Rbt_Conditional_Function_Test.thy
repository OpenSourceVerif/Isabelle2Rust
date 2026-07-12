theory Rbt_Conditional_Function_Test
  imports "HOL-Library.RBT_Impl" "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: RBT_Impl.rs `rbt_union_rec` and
   `rbt_inter_rec` -- E0308 followed by E0282 inference failures).

   Each function conditionally replaces a three-argument merge callback with
   `(\<lambda>k v v'. f k v' v)` and stores the selected callback in a tuple.
   Both HOL branches have the same function type.  Rust nevertheless infers the
   first branch as the concrete `Rc<closure>` type and rejects the other branch,
   which is `Rc<dyn Fn(A, B, B) -> B>`; the later RBT type-annotation errors are
   consequences of that failed tuple unification.

   The generated conditional must coerce every branch to the shared trait-
   object function type before constructing the tuple. *)

export_code RBT_Impl.rbt_union_rec RBT_Impl.rbt_inter_rec in Rust

end
