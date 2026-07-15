session Rust = Main +
  options [timeout = 600]
  sessions
    "HOL-Library"
  theories
    Rust_Setup
    Rust_BigInt_Int_Setup
    Rust_BigInt_Nat_Setup

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
