theory Cons_Mono_Test
  imports Main "Rust.Rust_Setup"
begin


definition c :: int where "c \<equiv> 42"

export_code c in Rust

end