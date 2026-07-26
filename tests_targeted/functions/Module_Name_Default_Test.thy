theory Module_Name_Default_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* A Rust export without an explicit module_name must retain Code_Namespace's
   conventional theory-derived module.  Its generated statements therefore live
   in Module_Name_Default_Test.rs and src/lib.rs declares that module; an explicit
   empty identifier prefix must not erase the inferred module before assembly. *)

definition default_module_value :: bool where
  "default_module_value = True"

export_code default_module_value in Rust

end
