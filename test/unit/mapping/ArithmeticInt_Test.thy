theory ArithmeticInt_Test
  imports Main "Rust.Rust_BigInt_Int_Setup"
begin

(* Rust_BigInt_Int_Setup maps int/integer arithmetic and bit operations to BigInt. *)

unbundle bit_operations_syntax

definition int_affine :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_affine x y = 3 * x - y + 7"

definition int_branch :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_branch x y = (if x < y then y - x else x - y)"

definition int_from_integer :: "integer \<Rightarrow> int" where
  "int_from_integer k = int_of_integer k"

definition int_to_integer :: "int \<Rightarrow> integer" where
  "int_to_integer k = integer_of_int k"

definition integer_zero :: integer where
  "integer_zero = 0"

definition integer_affine :: "integer \<Rightarrow> integer \<Rightarrow> integer" where
  "integer_affine x y = 3 * x - y + 7"

definition integer_neg_abs :: "integer \<Rightarrow> integer" where
  "integer_neg_abs x = abs (- x)"

definition integer_eq :: "integer \<Rightarrow> integer \<Rightarrow> bool" where
  "integer_eq x y = (x = y)"

definition integer_le :: "integer \<Rightarrow> integer \<Rightarrow> bool" where
  "integer_le x y = (x \<le> y)"

definition integer_lt :: "integer \<Rightarrow> integer \<Rightarrow> bool" where
  "integer_lt x y = (x < y)"

definition integer_dup :: "integer \<Rightarrow> integer" where
  "integer_dup x = Code_Numeral.dup x"

(* Code_Numeral.sub is an internal panic fallback, not a direct user export. *)

definition integer_divmod_abs :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer" where
  "integer_divmod_abs x y = Code_Numeral.divmod_abs x y"

definition integer_bits :: "integer \<Rightarrow> integer \<Rightarrow> integer" where
  "integer_bits x y = (x AND y) + (x OR y) + (x XOR y)"

definition integer_not :: "integer \<Rightarrow> integer" where
  "integer_not x = NOT x"

export_code
  int_affine int_branch int_from_integer int_to_integer integer_zero
  integer_affine integer_neg_abs integer_eq integer_le integer_lt
  integer_dup integer_divmod_abs integer_bits integer_not
  in Rust

end
