theory Rec_Set_Test
  imports   
    Main "Rust.Rust_Setup"
begin

datatype  option = None | Some int | Rec option

fun set :: "option \<Rightarrow> int \<Rightarrow> option" where
  "set (Some _) x = Some x" |
  "set None x = Some x" |
  "set (Rec op) x = Rec (set op x)"

export_code set in Rust
                     
end