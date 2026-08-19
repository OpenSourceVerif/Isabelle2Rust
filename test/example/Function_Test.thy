theory Function_Test
  imports Main "Rust.Rust_Base_Setup"
begin

hide_const (open) List.length

fun length :: "'a list \<Rightarrow> nat" where
  "length Nil = 0"
| "length (Cons _ xs) = Suc (length xs)"

export_code length in Rust

end
