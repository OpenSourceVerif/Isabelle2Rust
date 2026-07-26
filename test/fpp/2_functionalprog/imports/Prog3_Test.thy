theory Prog3_Test
imports Main Prog1_Test Prog2_Test "Rust.Rust_Base_Setup"
begin
value "sub 1 2"
value "Prog1_Test.sub 1 2"
value "Prog2_Test.sub 1 2"

export_code Prog1_Test.add Prog1_Test.sub Prog2_Test.add Prog2_Test.sub in Rust

end
