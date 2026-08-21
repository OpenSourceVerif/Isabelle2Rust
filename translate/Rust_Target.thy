theory Rust_Target
  imports Main
begin

text \<open>
  Core Rust target registration and serialization support.  This theory does
  not install any target-specific code adaptations.
\<close>

ML_file \<open>code_debug_info.ML\<close>
ML_file \<open>code_rust.ML\<close>

end
