theory Func_Max_If_Test
  imports
  Main "Rust.Rust_Setup"
begin

fun max:: "int \<Rightarrow> int \<Rightarrow> int" where
" max a b = (if a > b then a else b) 
"

export_code max in Rust 

end