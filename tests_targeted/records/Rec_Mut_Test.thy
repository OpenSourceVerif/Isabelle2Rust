theory Rec_Mut_Test
  imports   
    Main "Rust.Rust_Setup"
begin

(* Mutually recursive functions over two user-defined option datatypes *)

datatype  aoption = Nonea | Somea int | MutualReca boption
  and  boption = Noneb | Someb int | MutualRecb aoption

fun mugeta :: "aoption \<Rightarrow> int" 
  and mugetb :: "boption \<Rightarrow> int" where
" mugeta (Somea x) = x" | 
" mugeta Nonea = 0" | 
" mugeta (MutualReca bop) = mugetb bop" |
" mugetb (Someb x) = x" | 
" mugetb Noneb = 0" | 
" mugetb (MutualRecb aop) = mugeta aop" 

export_code mugeta in Rust

end