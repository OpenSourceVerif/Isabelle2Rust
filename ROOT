session Rust = Main +
  options [timeout = 600]
  sessions
    "HOL-Library"
  directories
    "translate"
  theories
    "translate/Rust_Target"
    "translate/Rust_Base_Setup"
    "translate/Rust_Integer_BigInt_Layer"
    "translate/Rust_BigInt_Setup"
    "translate/Rust_Checked128_Setup"
    "translate/Rust_BigInt_WordU128_Setup"
    "translate/Rust_Checked128_WordU128_Setup"

session "Rust-HOL-Codegenerator_Test" in "test/HOL_Codegenerator" = "HOL-Library" +
  description "Rust stress test session for a broad HOL code-generator export"
  options [timeout = 1200]
  sessions
    Rust
    "HOL-Number_Theory"
    "HOL-Data_Structures"
    "HOL-Examples"
  theories [document = false, condition = ISABELLE_CARGO]
    Candidates
    Generate
    Generate_Binary_Nat
  export_files (in "stage1/Generate") [2]
    "Rust-HOL-Codegenerator_Test.Generate:code/**"
  export_files (in "stage1/Generate_Binary_Nat") [2]
    "Rust-HOL-Codegenerator_Test.Generate_Binary_Nat:code/**"
