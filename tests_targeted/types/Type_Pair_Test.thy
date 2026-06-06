theory Type_Pair_Test
  imports Main "Rust.Rust_Setup"
begin

definition int_pair :: "int \<Rightarrow> (int \<times> int)" where
  "int_pair x = (x, x)"

export_code int_pair in Rust

end
