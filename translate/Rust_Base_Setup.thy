theory Rust_Base_Setup
  imports Rust_Target
begin

text \<open>
  Representation-independent Rust code-generation support.  Numeric
  representations are selected separately by exactly one of
  \<^theory_text>\<open>Rust_BigInt_Setup\<close>,
  \<^theory_text>\<open>Rust_Source_BigInt_Setup\<close>,
  \<^theory_text>\<open>Rust_Dashu_Setup\<close>, or
  \<^theory_text>\<open>Rust_Checked128_Setup\<close>.  The BigInt and Checked128
  profiles also provide optional \<^verbatim>\<open>WordU128\<close> setups.
\<close>

(** module remapping to prevent module dependency problem **)

code_identifier
  code_module Nat \<rightharpoonup> (Rust) Arith
| code_module Num \<rightharpoonup> (Rust) Arith
| code_module Groups \<rightharpoonup> (Rust) Arith
| code_module Power \<rightharpoonup> (Rust) Arith
| code_module Code_Numeral \<rightharpoonup> (Rust) Arith

(* Code.abort is a primitive with two protocol arguments. Its Rust printing
   is handled in Code_Rust: dynamic literal messages need decoding, the delayed
   argument must stay unevaluated, and the result may have a function type.
   A generic mixfix printer cannot express those evaluation/typing boundaries.
   Keep a registration for target projection, and reject accidental fallback to
   the generic syntax path instead of silently printing an incomplete macro. *)
setup \<open>
  Code_Target.set_printings (Code_Symbol.Constant
    (\<^const_name>\<open>Code.abort\<close>,
      [(Code_Rust.target, SOME (Code_Printer.complex_const_syntax
        (2, fn _ => fn _ => fn _ => fn _ => fn _ => fn _ =>
          error "Code.abort must use the Rust protocol printer")))]))
\<close>


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
