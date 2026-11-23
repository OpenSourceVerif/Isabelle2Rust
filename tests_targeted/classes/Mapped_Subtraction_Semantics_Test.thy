theory Mapped_Subtraction_Semantics_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  A single polymorphic subtraction operation is instantiated at nat, int and
  integer. Its dictionary must preserve truncated natural subtraction and signed
  integer subtraction even in the same export. The observations expose only
  Booleans, so runtime checks do not assume a particular numeric representation.
  Separate exports check each native implementation. The direct BigInt profile
  cannot combine signed and saturating subtraction in one Rust trait impl, so
  the mixed export must report that representation conflict. Source_BigInt's
  distinct receivers cover the successful mixed export in its companion test.
  Large literals exceed both 64-bit and 128-bit ranges.
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
  for export1, Int_Runtime for export2, and Integer_Runtime for export3.
\<close>

export_code natural_cases in Rust module_name MappedSubtraction
export_code int_cases in Rust module_name MappedSubtraction
export_code integer_cases in Rust module_name MappedSubtraction
ML \<open>
  val result = Exn.capture (fn () =>
    Code_Target.produce_code @{context} false
      [@{const_name natural_cases}, @{const_name int_cases}, @{const_name integer_cases}]
      "Rust" "MappedSubtraction" NONE []) ();
  val _ = (case result of
    Exn.Exn (ERROR message) =>
      if String.isSubstring "cannot merge distinct instances" message andalso
          String.isSubstring @{class minus} message
      then () else error message
  | Exn.Exn exn => Exn.reraise exn
  | Exn.Res _ => error "Signed and natural subtraction shared one Rust implementation");
\<close>

end
