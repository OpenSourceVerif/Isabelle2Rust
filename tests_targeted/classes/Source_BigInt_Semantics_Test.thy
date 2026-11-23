theory Source_BigInt_Semantics_Test
  imports Rust_Source_BigInt_Setup
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
  three fragments plus Operations_Runtime for export4; Multi_Runtime covers export5.
\<close>


definition arithmetic_observations :: "bool \<Rightarrow> bool list"
  where "arithmetic_observations b =
    (let z = (if b then -7 else 7) :: integer;
         n = (1361129467683753853853498429727072845824 :: nat)
     in [nat_of_integer (-3) = 0,
         integer_of_nat (nat_of_integer z) = max 0 z,
         integer_of_int (int_of_integer z) = z,
         nat (int n) = n,
         n + n = 2722258935367507707706996859454145691648,
         n * n = 1852673427797059126777135760139006525652319754650249024631321344126610074238976,
         (n div 3) * 3 + n mod 3 = n,
         (n div 0) = 0, n mod 0 = n,
         (z div 3) * 3 + z mod 3 = z,
         (z div (-3)) * (-3) + z mod (-3) = z,
         (z div 0) = 0, z mod 0 = z,
         abs z = 7, -z + z = 0,
         (Bit_Operations.and z 3) = (if b then 1 else 3),
         (Bit_Operations.or z 2) = (if b then -5 else 7),
         (Bit_Operations.xor z 3) = (if b then -6 else 4),
         Bit_Operations.not z = -z - 1,
         gcd (int_of_integer z) 12 = 1,
         lcm (int_of_integer z) 12 = 84])"

definition generic_twice_minus :: "'a::{plus,minus} \<Rightarrow> 'a \<Rightarrow> 'a"
  where "generic_twice_minus x y = (x + x) - y"

definition mixed_container_observations :: "bool list"
  where "mixed_container_observations =
    [generic_twice_minus (1::nat) 3 = 0,
     generic_twice_minus (1::int) 3 = -1,
     generic_twice_minus (1::integer) 3 = -1,
     map (\<lambda>(n,z,k). integer_of_nat n + integer_of_int z + k)
       [(2::nat,-3::int,4::integer)] = [3]]"

lemma wrapper_observations:
  "arithmetic_observations False = replicate 21 True"
  "arithmetic_observations True = replicate 21 True"
  "mixed_container_observations = replicate 4 True"
  by (eval)+

export_code natural_cases in Rust module_name SourceBigInt
export_code int_cases in Rust module_name SourceBigInt
export_code integer_cases in Rust module_name SourceBigInt
export_code natural_cases int_cases integer_cases arithmetic_observations mixed_container_observations in Rust module_name SourceBigInt

export_code natural_cases int_cases integer_cases arithmetic_observations mixed_container_observations in Rust

end
