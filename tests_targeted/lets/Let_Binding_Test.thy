theory Let_Binding_Test
  imports Main "Rust.Rust_Setup"
begin

definition test_let :: "nat \<Rightarrow> nat" where
"test_let n \<equiv> (
   let x = n + 1 
   in x * 2
 )"

export_code test_let in Rust

end