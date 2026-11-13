theory Word_Setup_Common
  imports "HOL-Library.Word"
begin

unbundle bit_operations_syntax

definition word_arithmetic ::
    "64 word \<Rightarrow> 64 word \<Rightarrow> nat \<Rightarrow>
      64 word \<times> 64 word \<times> 64 word \<times> 64 word" where
  "word_arithmetic x y n = (x + y, x - y, x * y, x ^ n)"

definition word_div_mod ::
    "64 word \<Rightarrow> 64 word \<Rightarrow> 64 word \<times> 64 word" where
  "word_div_mod x y = (x div y, x mod y)"

definition word_bits ::
    "64 word \<Rightarrow> 64 word \<Rightarrow> nat \<Rightarrow>
      64 word \<times> 64 word \<times> 64 word \<times> 64 word \<times> bool" where
  "word_bits x y n = (x AND y, x OR y, x XOR y, take_bit n (push_bit n x), bit x n)"

definition word_casts ::
    "8 word \<Rightarrow> 64 word \<times> int \<times> nat" where
  "word_casts x = (ucast x, sint x, unat x)"

definition word_signed_compare ::
    "64 word \<Rightarrow> 64 word \<Rightarrow> bool \<times> bool" where
  "word_signed_compare x y = (x <s y, x \<le>s y)"

definition word_mask :: "nat \<Rightarrow> 64 word" where
  "word_mask n = mask n"

end
