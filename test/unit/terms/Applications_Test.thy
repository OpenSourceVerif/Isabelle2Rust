theory Applications_Test
  imports Main "Rust.Rust_Setup"
begin

definition make_triple :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "make_triple x y z = (x, y, z)"

definition direct_triple :: "bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "direct_triple x = make_triple x True False"

definition call_and_reuse :: "bool \<Rightarrow> (bool \<times> bool \<times> bool) \<times> bool" where
  "call_and_reuse x = (make_triple x True False, x)"

definition carry3 :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool)" where
  "carry3 c = (\<lambda>x y. (c, x, y))"

definition call_returned :: "bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "call_returned c x = ((carry3 c) x) False"

definition lambda_call :: "'a \<Rightarrow> 'a" where
  "lambda_call x = (\<lambda>y. y) x"

definition nested_lambda_call :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b" where
  "nested_lambda_call x y = ((\<lambda>f. f y) (\<lambda>z. (x, z)))"

(* Unsaturated applications of top-level constants. *)
definition offset_sum :: "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "offset_sum n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

definition test_offset_sum :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_offset_sum x \<equiv> (\<lambda>y. ((offset_sum 1) x) y)"

definition offset_sum2 :: "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "offset_sum2 n x = (\<lambda>y. (\<lambda>z. x + y + z + n))"

definition test_offset_sum2 :: "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_offset_sum2 x = (\<lambda>y. \<lambda>z. ((offset_sum2 1 z) x) y)"

definition sum3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "sum3 x y z = x + y + z"

definition partial_sum3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "partial_sum3 n = sum3 n"

definition partial_triple :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool)" where
  "partial_triple x = make_triple x"

definition call_partial_triple :: "bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool \<times> bool" where
  "call_partial_triple x y = partial_triple x y x"

definition test_carry3 :: "bool \<Rightarrow> bool \<Rightarrow> (bool \<Rightarrow> bool \<times> bool \<times> bool)" where
  "test_carry3 c x = (\<lambda>y. ((carry3 c) x) y)"

export_code
  direct_triple call_and_reuse carry3 call_returned lambda_call nested_lambda_call
  test_offset_sum test_offset_sum2 partial_sum3 call_partial_triple test_carry3
  in Rust

end
