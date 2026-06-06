theory Func_Max_Case_Test
  imports
  Main "Rust.Rust_Setup"
begin

fun max2:: "int \<Rightarrow> int \<Rightarrow> int" where
"max2 a b = (
   case a > b of
     True \<Rightarrow> a |
     False \<Rightarrow> b )
"

export_code max2 in Rust

end