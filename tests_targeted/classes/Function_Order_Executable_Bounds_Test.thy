theory Function_Order_Executable_Bounds_Test
  imports "HOL.Enum" "Rust.Rust_Base_Setup"
begin

(* The executable strict-order equation for HOL functions enumerates the domain
   and compares two codomain results for inequality.  Its logical function-order
   instance requires only 'b::order, while code generation introduces the
   additional operational dictionary 'b::equal.  The Rust reconstruction must
   retain that method-body dictionary in the pointwise Ord implementation for
   Rc<dyn Fn(A) -> B>; otherwise the emitted call to HOL::eq fails with E0277
   because B: Equal is absent. *)
definition executable_function_less ::
  "('a::enum \<Rightarrow> 'b::order) \<Rightarrow> ('a \<Rightarrow> 'b) \<Rightarrow> bool"
where
  "executable_function_less f g \<longleftrightarrow> f < g"

export_code executable_function_less in Rust

end
