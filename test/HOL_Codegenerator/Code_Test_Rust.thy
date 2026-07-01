theory Code_Test_Rust
imports
  "HOL-Library.Code_Test"
  "Rust.Rust_BigInt_Int_Setup"
begin

text \<open>Test cases for \<^text>\<open>test_code\<close>\<close>

definition gcd_test_integer :: "bool"  where
"gcd_test_integer = ((gcd 15 5 = (5 :: integer))
\<and> (gcd 15 (- 10) = (5 :: integer))
\<and> (gcd (- 10) 15 = (5 :: integer))
\<and> (gcd (- 10) (- 15) = (5 :: integer))
\<and> (gcd 0 (- 10) = (10 :: integer))
\<and> (gcd (- 10) 0 = (10 :: integer))
\<and> (gcd 0 0 = (0 :: integer)))"

definition gcd_test_int :: "bool"  where
"gcd_test_int = ((gcd (15::int) 5 = 5) 
\<and> (gcd (15::int) (-10) = 5)
\<and> (gcd ((-10)::int) 15 = 5)
\<and> (gcd ((-10)::int) (-15) = 5)
\<and> (gcd (0::int) (-10) = 10)
\<and> (gcd ((-10)::int) 0 = 10)
\<and> (gcd (0::int) 0 = 0))"

definition gcd_test :: "bool" where
"gcd_test = (gcd_test_integer \<and> gcd_test_int)"

export_code gcd_test in Rust

end
