theory x64EncodeRustGenerator
  imports
    Main
    x64Assembler
    "Rust.Rust_BigInt_WordU128_Setup"
begin

text \<open>
  This generator exports the same raw x64 encoder definition used by the fixed
  OCaml validation baseline.  Keeping the exported HOL constant unchanged is
  essential for later cross-language performance measurements: instruction
  parsing and result conversion belong to the external validation harness, not
  to the generated encoder itself.
\<close>

text \<open>
  Signed Isabelle word widths use the same phantom width marker as unsigned
  words in the established u128 Rust word setup.  The encoder entry point stays
  the unmodified HOL constant; this declaration only selects its Rust target
  representation.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code x64_encode in Rust
  module_name X64_encode file_prefix x64_encode

end
