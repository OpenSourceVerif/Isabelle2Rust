theory Abs_Poly_Test
  imports Main "Rust.Rust_Setup"
begin


definition id :: "'a \<Rightarrow> 'a" where
  "id \<equiv> (\<lambda>x. x)"

export_code id in Rust

end
