theory Case_Poly_Test
  imports Main "Rust.Rust_Setup"
begin


fun Id :: "'a \<Rightarrow> 'a" where
  "Id x = (case x of y \<Rightarrow> y)"

export_code Id in Rust

end
