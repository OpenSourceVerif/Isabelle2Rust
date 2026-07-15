theory Undefined_Function_Value_Test
  imports Main "Rust.Rust_Setup"
begin

(* A polymorphic constant without executable code equations is emitted as a
   nullary Rust panic stub returning its complete HOL value.  At a function
   type, applying that value must first invoke the stub and then invoke the
   returned Rc<dyn Fn>; treating the source argument as an argument of the stub
   instead produces a Rust wrong-arity error. *)
definition apply_undefined_function :: "bool \<Rightarrow> bool" where
  "apply_undefined_function x = (undefined :: bool \<Rightarrow> bool) x"

export_code apply_undefined_function in Rust

end
