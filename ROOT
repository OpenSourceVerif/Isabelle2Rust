session Rust = Main +
  options [timeout = 600]
  theories
    Rust_Setup

session Test in "tests_targeted" = Rust +
  description "List_Test test session"
  options [timeout = 300]
  theories [document = false]
    "List_Test"
  export_files (in "Rust_Out/List_Test") [2]
    "*:**.rs"
    "*:**.toml"
