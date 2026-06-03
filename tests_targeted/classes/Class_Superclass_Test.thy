theory Class_Superclass_Test
  imports Main "Rust.Rust_Setup"
begin

class add1 =
  fixes add1 :: "'a \<Rightarrow> 'a"

class add2 =
  fixes add2 :: "'a \<Rightarrow> 'a"

class add1_add2 = add1 + add2

fun add12 :: "('a::add1_add2) \<Rightarrow> 'a" where
  "add12 x = add2 (add1 x)"

export_code add12 in Rust 
end
