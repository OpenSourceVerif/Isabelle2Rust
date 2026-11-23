theory Runtime_Box_Name_Test
  imports Rust_Base_Setup
begin

text \<open>
  A HOL datatype named box keeps the generated nominal name Box. Recursive
  fields of an unrelated datatype still require the standard library's heap
  Box, in both their declarations and their constructor expressions. The two
  representations must remain distinct when building and matching nested
  recursive values inside the user datatype.
\<close>

datatype 'a box = UserBox 'a
datatype spine = Stop | Step bool spine

definition pack :: "bool \<Rightarrow> bool \<Rightarrow> spine box"
  where "pack a b = UserBox (Step a (Step b Stop))"

fun inspect :: "spine box \<Rightarrow> bool \<times> bool" where
  "inspect (UserBox (Step a (Step b xs))) = (a, b)"
| "inspect _ = (False, False)"

fun flip :: "spine \<Rightarrow> spine" where
  "flip Stop = Stop"
| "flip (Step b xs) = Step (\<not>b) (flip xs)"

fun unpack :: "'a box \<Rightarrow> 'a" where
  "unpack (UserBox x) = x"

export_code pack inspect flip unpack in Rust module_name RuntimeBoxName

end
