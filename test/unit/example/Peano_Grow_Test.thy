theory Peano_Grow_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype peano =
    Z
  | S peano

fun bump :: "peano \<Rightarrow> peano" where
  "bump n = S (S n)"

definition grow :: "peano \<Rightarrow> peano" where
  "grow n =
    (let x = n in
     let x = S x in
     let x = bump x in
     let x = S x in x)"

export_code grow in Rust

end
