theory Rust_Setup
  imports "Main"
begin

ML_file \<open>code_debug_info.ML\<close>
ML_file \<open>code_rust.ML\<close>



(** module remapping to prevent module dependency problem **)

code_identifier
  code_module Nat \<rightharpoonup> (Rust) Arith
| code_module Num \<rightharpoonup> (Rust) Arith
| code_module Groups \<rightharpoonup> (Rust) Arith
| code_module Power \<rightharpoonup> (Rust) Arith
| code_module Code_Numeral \<rightharpoonup> (Rust) Arith

code_printing
  constant Code.abort \<rightharpoonup> (Rust) "panic'!( _ )"


(* Bools *)
code_printing
  type_constructor bool \<rightharpoonup> 
    (Rust) "bool"
| constant False \<rightharpoonup> 
    (Rust) "false"
| constant True \<rightharpoonup> 
    (Rust) "true"

code_printing
  constant Not \<rightharpoonup>
    (Rust) "'! _"
| constant HOL.conj \<rightharpoonup>
    (Rust) infixl 3 "&&"
| constant HOL.disj \<rightharpoonup>
    (Rust) infixl 2 "||"
| constant HOL.If \<rightharpoonup>
    (Rust) "!if _ { _ } else { _ }"


code_reserved
  (Rust) bool


(* Tuples *)
code_printing
  type_constructor "Product_Type.prod" \<rightharpoonup>
    (Rust) "!(_, _)"
| constant "Product_Type.Pair" \<rightharpoonup>
    (Rust) "!(_, _)"

end
