theory Case_Option_Test
  imports Main "Rust.Rust_Setup"
begin

fun get_or_zero :: "int option \<Rightarrow> int" where
  "get_or_zero x = (case x of None \<Rightarrow> 0 | Some n \<Rightarrow> n)"

export_code get_or_zero in Rust

end
