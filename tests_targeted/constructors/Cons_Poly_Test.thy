theory Cons_Poly_Test
  imports Main "Rust.Rust_Setup"
begin


definition zero :: "'a::zero" where "zero \<equiv> 0"  
  
export_code zero in Rust


end