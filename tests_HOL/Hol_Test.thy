theory Hol_Test
imports
  "HOL-Library.Code_Test"
  "Rust.Rust_Setup"
  Code_Lazy_Test
begin

text \<open>Test cases for \<^text>\<open>test_code\<close>\<close>

definition gcd_test :: "bool"  where
"gcd_test = ((gcd (15::int) 5 = 5) 
\<and> (gcd (15::int) (-10) = 5)
\<and> (gcd ((-10)::int) 15 = 5)
\<and> (gcd ((-10)::int) (-15) = 5)
\<and> (gcd (0::int) (-10) = 10)
\<and> (gcd ((-10)::int) 0 = 10)
\<and> (gcd (0::int) 0 = 0))"

export_code gcd_test in Rust

end
