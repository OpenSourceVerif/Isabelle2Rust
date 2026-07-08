theory ReturnPolymorphism_Test
  imports Main "Rust.Rust_Setup"
begin

(* The result type variable is fixed by the expected return type, not arguments. *)

class pseudo_num =
  fixes pn_zero :: "'a"
    and pn_one :: "'a"
    and pn_add :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun conv :: "nat \<Rightarrow> 'a::pseudo_num" where
  "conv 0 = pn_zero"
| "conv (Suc n) = (let m = conv n in pn_add (pn_add m m) pn_one)"

export_code
  conv
  in Rust

end
