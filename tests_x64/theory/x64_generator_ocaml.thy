theory x64_generator_ocaml
  imports
    Main
    x64Assembler
    x64Semantics
begin

text \<open>
  Shared OCaml reference exports for x64 encoder and single-step validation.
  This theory deliberately does not import a Rust numeric profile.
\<close>

export_code x64_encode in OCaml
  module_name x64_encode file_prefix x64_encode

export_code x64_step_test in OCaml
  module_name x64_step_test file_prefix x64_step_test

end
