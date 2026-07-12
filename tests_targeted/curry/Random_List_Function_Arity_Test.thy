theory Random_List_Function_Arity_Test
  imports "HOL.Quickcheck_Random" "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: List.rs `random_aux_list`, with the
   same family in Quickcheck_Random.rs, Records.rs and String.rs --
   E0593/E0308, whose callback-coercion form is E0631).

   The random generator is assembled from state combinators whose arguments and
   results are themselves multi-argument function values.  A combinator slot
   often expects one outer argument returning another function, while the
   backend flattens all adjacent HOL arrows into one Rust closure.  For example,
   a callback expected as `Fn(X) -> Rc<dyn Fn(State) -> Result>` is emitted as
   `move |x, state| ...`; rustc reports that a unary closure takes two arguments,
   followed by closure-signature and tuple-result mismatches.

   Re-exporting the list generator pins the compact library representative of
   the remaining 66 E0593 and 53 E0631 diagnostics in Generate.  Correct Rust
   must preserve each higher-order callback boundary while choosing the closure
   arity for the function value on that side of the boundary. *)

export_code List.random_aux_list in Rust

end
