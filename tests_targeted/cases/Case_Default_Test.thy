theory Case_Default_Test
  imports Main "Rust.Rust_Setup"
begin

datatype color = Red | Green | Blue | Other nat

fun is_primary :: "color \<Rightarrow> bool" where
  "is_primary Red = True"
| "is_primary Green = True"
| "is_primary Blue = True"
| "is_primary _ = False"

export_code is_primary in Rust

end
