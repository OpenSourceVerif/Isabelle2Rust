theory Runtime_Sign_Collision_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  A user datatype named sign becomes Sign in Rust. A numeric literal in the
  same generated module must use num_bigint::Sign::Plus, even though the
  backend imports the runtime with a glob. The unqualified Sign::Plus selected
  the user enum and failed with E0599. Check positive and negative numerals.
\<close>

datatype sign = LocalSign
definition sign_literal :: "sign \<Rightarrow> sign \<times> integer \<times> integer"
  where "sign_literal s = (s, 257, -513)"

export_code sign_literal in Rust module_name Collision

end
