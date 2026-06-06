theory Class_No_Ins_Test
  imports Main "Rust.Rust_Setup"
begin

class inc =
  fixes inc :: "'a \<Rightarrow> 'a"

fun add1 :: "('a::inc) \<Rightarrow> 'a" where
  "add1 x = inc x"

export_code add1 in Rust

end
