theory Case_Length2_Test
  imports Main "Rust.Rust_Setup"
begin

fun length2 :: "int list \<Rightarrow> int" where
  "length2 xs = (case xs of [] \<Rightarrow> 0 | [x] \<Rightarrow> x*3 | _ \<Rightarrow> 0)" 

export_code length2 in Rust 

end
