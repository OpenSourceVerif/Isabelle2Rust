theory Rec_Get_Test
  imports   
    Main "Rust.Rust_Setup"
begin


datatype  option = None | Some int | Rec option

fun get :: "option \<Rightarrow> int" where
" get (Some x) = x" | 
" get None = 0" |
" get (Rec op) = get op" 

export_code get in Rust
                     
end