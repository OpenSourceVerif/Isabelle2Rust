theory Case_Length1_Test
  imports Main "Rust.Rust_Setup"
begin

fun length1 :: "'a list \<Rightarrow> bool" where
  "length1 xs = (case xs of [] \<Rightarrow> False | [x] \<Rightarrow> True | _ \<Rightarrow> False)" 

export_code length1 in Rust
end
