theory Module_Collision_Test
  imports Main "Rust.Rust_Setup" "Go.Go_Setup"
begin

(* Regression target for H4 (D.4): two constants forced into DIFFERENT modules
   with the SAME base name, both referenced from a third module.

   The old modify_deresolver truncates every resolved name to its last segment
   and compensates with `use crate::<mod>::*;` glob imports. With two modules
   each exporting a `dup`, the importer's flat namespace gets two `dup` globs ->
   ambiguous reference (rustc E0659). A qualified deresolve (crate::ModA::dup vs
   crate::ModB::dup) removes the ambiguity. *)

definition alpha :: nat where "alpha = 0"
definition beta :: nat where "beta = 0"

definition use_both :: nat where "use_both = alpha + beta"

code_identifier
  constant alpha \<rightharpoonup> (Rust) "ModA.dup"
| constant beta  \<rightharpoonup> (Rust) "ModB.dup"

export_code use_both in Rust
 (* module_name Use_both*)
 (*export_code use_both in Go*)

end
