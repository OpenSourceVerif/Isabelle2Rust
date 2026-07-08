theory ModuleResolution_Test
  imports Main "Rust.Rust_Setup"
begin

(* Equal Rust basenames from different modules must remain qualified. *)

definition alpha :: nat where
  "alpha = 0"

definition beta :: nat where
  "beta = 0"

definition use_both :: nat where
  "use_both = alpha + beta"

code_identifier
  constant alpha \<rightharpoonup> (Rust) "ModA.dup"
| constant beta  \<rightharpoonup> (Rust) "ModB.dup"

export_code
  use_both
  in Rust

end
