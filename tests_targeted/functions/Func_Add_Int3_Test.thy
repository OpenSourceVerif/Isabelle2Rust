theory Func_Add_Int3_Test
  imports Main "Rust.Rust_Setup"
begin

definition add3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add3 x y z = x + y + z"

export_code add3 in Rust

end
