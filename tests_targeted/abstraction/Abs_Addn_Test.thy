theory Abs_Addn_Test
  imports Main "Rust.Rust_Setup"
begin


definition add_n :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "add_n n \<equiv> (\<lambda>x. x + n)" 

export_code add_n in Rust

end
