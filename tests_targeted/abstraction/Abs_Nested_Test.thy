theory Abs_Nested_Test
  imports Main "Rust.Rust_Setup"
begin

definition add_n_2 ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
"add_n_2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

export_code add_n_2 in Rust

end
