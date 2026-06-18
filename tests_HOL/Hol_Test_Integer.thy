theory Hol_Test_Integer
imports
  "HOL-Library.Code_Test"
  "Rust.Rust_BigInt_Int_Setup"
  Code_Lazy_Test
begin

text \<open>Test cases for \<^text>\<open>test_code\<close>\<close>

definition gcd_test :: "bool"  where
"gcd_test = ((gcd 15 5 = (5 :: integer))
\<and> (gcd 15 (- 10) = (5 :: integer))
\<and> (gcd (- 10) 15 = (5 :: integer))
\<and> (gcd (- 10) (- 15) = (5 :: integer))
\<and> (gcd 0 (- 10) = (10 :: integer))
\<and> (gcd (- 10) 0 = (10 :: integer))
\<and> (gcd 0 0 = (0 :: integer)))"

export_code gcd_test in Rust

end
