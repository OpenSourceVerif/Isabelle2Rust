theory Func_Add_Int_Test
  imports Main "Rust.Rust_Setup"
begin


fun add_int :: "int \<Rightarrow> int \<Rightarrow> int" where
  "add_int x y = x + y"
declare [[code_preproc_trace only: add_int]]
print_codeproc

export_code add_int in Rust

end