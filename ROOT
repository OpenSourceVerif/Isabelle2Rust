session Rust = Main +
  options [timeout = 600]
  sessions
    "HOL-Library"
  theories
    Rust_Base_Setup
    Rust_Integer_BigInt_Layer
    Rust_BigInt_Setup
    Rust_Integer_Hybrid128_Layer
    Rust_Hybrid128_Setup
    Rust_Checked128_Setup
    Rust_BigInt_WordU128_Setup
    Rust_Hybrid128_WordU128_Setup
    Rust_Checked128_WordU128_Setup

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
