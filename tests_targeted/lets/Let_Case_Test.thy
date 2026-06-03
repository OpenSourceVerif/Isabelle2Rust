theory Let_Case_Test
  imports Main "Rust.Rust_Setup"
begin

fun add1 :: "int \<Rightarrow> int" where
  "add1 x = (let z = 1 in case z of y \<Rightarrow> (y+z))"

export_code add1 in Rust 

end
