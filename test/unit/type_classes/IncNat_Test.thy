theory IncNat_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Instance_Nat_Test"


class inc =
  fixes inc :: "'a \<Rightarrow> 'a"

instantiation nat
 :: inc
begin
  definition inc_nat where "inc (n::nat) = n + 1"
  instance ..
end

fun add2 :: "nat \<Rightarrow> nat" where
  "add2 x = inc x"

export_code
  add2
  in Rust

end
