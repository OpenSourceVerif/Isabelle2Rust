theory Prog2_Test
imports Main "Rust.Rust_Base_Setup"
begin
definition "add x y \<equiv> (x :: int) + y + 1"
definition "sub x y \<equiv> (x::int) - y - 1"

export_code add sub in Rust

end
