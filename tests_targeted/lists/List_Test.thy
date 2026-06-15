theory List_Test
  imports Main
    Main "Rust.Rust_Setup"
begin

(* A polymorphic list type and its length function*)

datatype 'a list =
  Nil 
  | Cons (head : 'a) (tail : "'a list")

fun length :: "'a list \<Rightarrow> nat" where
  "length Nil = 0"
| "length (Cons _ xs) = Suc (length xs)"


declare [[code_preproc_trace only: length]]

export_code length in Rust


end