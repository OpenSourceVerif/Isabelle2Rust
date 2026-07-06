theory Lists_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From List_Cons_Test"


definition n :: nat where "n \<equiv> length [1::nat,2,3]"

subsection "From List_Test"


(* A polymorphic list type and its length function*)

datatype 'a list =
  Nil 
  | Cons (head : 'a) (tail : "'a list")

fun length :: "'a list \<Rightarrow> nat" where
  "length Nil = 0"
| "length (Cons _ xs) = Suc (length xs)"


declare [[code_preproc_trace only: length]]

export_code
  n length
  in Rust

end
