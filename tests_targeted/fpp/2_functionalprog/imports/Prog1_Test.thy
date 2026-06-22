theory Prog1_Test
imports Main "Rust.Rust_Setup"
begin
definition "add x y \<equiv> (x :: int) + y"
definition "sub x y \<equiv> (x::int) - y"

export_code add sub in Rust

end
