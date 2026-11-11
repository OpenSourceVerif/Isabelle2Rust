theory Mapped_Subtraction_Semantics_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  A single polymorphic subtraction operation is instantiated at nat, int and
  integer. Its dictionary must preserve truncated natural subtraction and signed
  integer subtraction even in the same export. The observations expose only
  Booleans, so runtime checks do not assume a particular numeric representation.
  Separate exports also prevent a mixed export from accidentally supplying a
  missing instance. Large literals exceed both 64-bit and 128-bit ranges.
\<close>

definition check_differences ::
  "('a::{minus,equal} \<times> 'a \<times> 'a) list \<Rightarrow> bool list"
  where "check_differences cases = map (\<lambda>(x,y,z). x - y = z) cases"

definition natural_cases :: "bool \<Rightarrow> bool list"
  where "natural_cases reverse_order = check_differences
    (let cases = [(1::nat,2,0), (0,1,0), (4,4,0), (7,2,5),
       (1361129467683753853853498429727072845824,1,
        1361129467683753853853498429727072845823),
       (1,1361129467683753853853498429727072845824,0)]
     in if reverse_order then rev cases else cases)"

definition int_cases :: "bool \<Rightarrow> bool list"
  where "int_cases reverse_order = check_differences
    (let cases = [(1::int,2,-1), (0,1,-1), (-4,-1,-3), (7,-2,9),
       (1361129467683753853853498429727072845824,1,
        1361129467683753853853498429727072845823),
       (1,1361129467683753853853498429727072845824,
        -1361129467683753853853498429727072845823)]
     in if reverse_order then rev cases else cases)"

definition integer_cases :: "bool \<Rightarrow> bool list"
  where "integer_cases reverse_order = check_differences
    (let cases = [(1::integer,2,-1), (0,1,-1), (-4,-1,-3), (7,-2,9),
       (1361129467683753853853498429727072845824,1,
        1361129467683753853853498429727072845823),
       (1,1361129467683753853853498429727072845824,
        -1361129467683753853853498429727072845823)]
     in if reverse_order then rev cases else cases)"

lemma subtraction_observations:
  "natural_cases False = replicate 6 True"
  "natural_cases True = replicate 6 True"
  "int_cases False = replicate 6 True"
  "int_cases True = replicate 6 True"
  "integer_cases False = replicate 6 True"
  "integer_cases True = replicate 6 True"
  by (eval)+

text \<open>
  For runtime verification, concatenate the common Runtime file with Nat_Runtime
  for export1, Int_Runtime for export2, Integer_Runtime for export3, and all
  three fragments for export4.
\<close>

export_code natural_cases in Rust module_name MappedSubtraction
export_code int_cases in Rust module_name MappedSubtraction
export_code integer_cases in Rust module_name MappedSubtraction
export_code natural_cases int_cases integer_cases in Rust module_name MappedSubtraction

end
