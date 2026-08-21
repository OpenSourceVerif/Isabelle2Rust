theory bpf_generator_checked128
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Checked128_WordU128_Setup"
begin

text \<open>
  RQ3 export profile.  Isabelle integers and naturals use checked i128/u128
  arithmetic, and Isabelle words use the native u128 word adapter.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
