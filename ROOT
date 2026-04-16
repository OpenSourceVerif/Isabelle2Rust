session Rust = Main +
  options [timeout = 600]
  theories
    Rust_Setup

session Test in "tests_unsolved" = Rust +
  description "List_Cons_Test test session"
  options [timeout = 300]
  theories [document = false]
    "List_Cons_Test"
  export_files (in "Rust_Out/List_Cons_Test") [2]
    "*:**.rs"
    "*:**.toml"
