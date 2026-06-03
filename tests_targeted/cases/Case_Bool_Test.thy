theory Case_Bool_Test
  imports Main "Rust.Rust_Setup"
begin

fun neg :: "bool \<Rightarrow> bool" where
  "neg b = (case b of True \<Rightarrow> False | False \<Rightarrow> True)"

export_code neg in Rust

end
