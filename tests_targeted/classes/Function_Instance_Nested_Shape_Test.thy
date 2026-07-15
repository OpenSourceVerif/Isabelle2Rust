theory Function_Instance_Nested_Shape_Test
  imports Main "Rust.Rust_Setup"
begin

(* HOL constructs the lattice instance for a function type pointwise and may
   apply that construction recursively when the codomain is itself a function.
   Consequently `inf` on binary relations dispatches first to the instance for
   `bool \<Rightarrow> (bool \<Rightarrow> bool)`, whose Rust `Self` representation is
   `Rc<dyn Fn(bool) -> Rc<dyn Fn(bool) -> bool>>`.  The finite Boolean domain
   also supplies the executable enumeration dictionary used by HOL's function
   order equations, keeping the test within the code generator's executable
   fragment.

   The semantic HOL type alone also admits the backend's ordinary flattened
   representation `Rc<dyn Fn(bool, bool) -> bool>`.  This regression requires the
   class-method call to recover the nested representation selected by the
   recursive function dictionary; otherwise rustc rejects both the `Inf`
   receiver and the two relation arguments with E0277/E0308.

   Dictionary elimination may also leave an ordinary polymorphic wrapper such
   as `HOL.equal` rather than a direct class-method symbol.  Its two arguments
   must receive the same dictionary-selected nested shape; otherwise Rust infers
   the wrapper's generic parameter as the flat relation trait object and cannot
   find the recursively unary `Equal` implementation. *)

definition relation_inf ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow>
   (bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow>
   bool \<Rightarrow> bool \<Rightarrow> bool" where
  "relation_inf p q = inf p q"

definition relation_equal ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow>
   (bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool" where
  "relation_equal p q \<longleftrightarrow> HOL.equal p q"

export_code relation_inf relation_equal in Rust

end
