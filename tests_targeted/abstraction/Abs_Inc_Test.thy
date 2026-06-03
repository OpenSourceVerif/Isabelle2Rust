theory Abs_Inc_Test
  imports Main "Rust.Rust_Setup"
begin

definition inc :: "int \<Rightarrow> int" where
  "inc \<equiv> (\<lambda>x. x + 1)"

export_code inc in Rust

end
