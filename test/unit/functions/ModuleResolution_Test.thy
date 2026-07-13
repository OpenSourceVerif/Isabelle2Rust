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

definition nested_alpha :: nat where
  "nested_alpha = 0"

definition nested_beta :: nat where
  "nested_beta = 0"

definition nested_sum :: nat where
  "nested_sum = nested_alpha + nested_beta"

definition use_nested :: nat where
  "use_nested = nested_sum"

code_identifier
  constant alpha \<rightharpoonup> (Rust) "ModA.dup"
| constant beta  \<rightharpoonup> (Rust) "ModB.dup"
| constant nested_alpha \<rightharpoonup> (Rust) "Outer.ModA.dup"
| constant nested_beta  \<rightharpoonup> (Rust) "Outer.ModB.dup"
| constant nested_sum   \<rightharpoonup> (Rust) "Outer.ModA.sum"

export_code
  use_both use_nested
  in Rust

end
