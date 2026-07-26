theory Mut_Nat_Test
  imports Main "Rust.Rust_BigInt_Setup"
begin


definition let_mut_nat :: "nat \<Rightarrow> nat" where
"let_mut_nat n =
  (let x = n in
   let x = x + 1 in
   let x = x * 2 in
   x)"

export_code let_mut_nat in Rust

end
