theory x64StepGenerator
  imports Main x64Semantics
begin

export_code x64_step_test in OCaml
  module_name x64_step_test file_prefix x64_step_test

end
