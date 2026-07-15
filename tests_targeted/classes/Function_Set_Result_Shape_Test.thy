theory Function_Set_Result_Shape_Test
  imports "HOL.Enum" "Rust.Rust_Setup"
begin

(* A finite set comprehension over a three-argument function is implemented by
   `Set.collect`.  Its `Enum` dictionary recursively selects the unary Rust
   representation
   `Rc<dyn Fn(bool) -> Rc<dyn Fn(bool) -> Rc<dyn Fn(bool) -> bool>>>`
   for the set element, although the same HOL function type normally prints as
   one flat three-argument trait object.

   The selected element representation must flow through `Set.collect`'s result
   and become the enclosing definition's Rust return shape.  If only the predicate
   argument receives that shape, the flat `Set<Rc<dyn Fn(bool, bool, bool) -> bool>>`
   return annotation forces Rust to infer the wrong `collect` type parameter,
   producing E0308 together with a missing `Enum` implementation. *)

definition selected_boolean_functions ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool) set" where
  "selected_boolean_functions = {f. f True False True}"

export_code selected_boolean_functions in Rust

end
