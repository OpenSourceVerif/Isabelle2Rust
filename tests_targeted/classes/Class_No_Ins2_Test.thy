theory Class_No_Ins2_Test
  imports Main "Rust.Rust_Setup"
begin

class plus =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun add_pair :: "('a::plus) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "add_pair x y = plus x y"

export_code add_pair in Rust

end
