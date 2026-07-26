theory Rec_Get_Test
  imports   
    Main "Rust.Rust_Base_Setup"
begin


datatype  option = None | Some int | Rec option

fun get :: "option \<Rightarrow> int" where
" get (Some x) = x" | 
" get None = 0" |
" get (Rec op) = get op" 

code_thms get

print_codeproc
(*declare [[code_preproc_trace only: get]]*)

export_code get in Rust

end