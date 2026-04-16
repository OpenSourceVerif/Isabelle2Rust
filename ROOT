session Rust = Main +
  options [timeout = 600]
  theories
    Rust_Setup

session Test in "tests_unsolved" = Rust +
  description "Lambda_Test test session"
  options [timeout = 300]
  theories [document = false]
    "Lambda_Test"
  export_files (in "Rust_Out/Lambda_Test") [2]
    "*:**.rs"
    "*:**.toml"
