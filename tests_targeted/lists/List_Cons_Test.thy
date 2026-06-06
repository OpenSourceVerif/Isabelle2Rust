theory List_Cons_Test
  imports Main "Rust.Rust_Setup"
begin

definition n :: nat where "n \<equiv> length [1::nat,2,3]"

export_code n in Rust

end
