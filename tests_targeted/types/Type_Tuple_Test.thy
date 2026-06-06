theory Type_Tuple_Test
  imports Main "Rust.Rust_Setup"
begin


(* Type test: *)

fun swap :: "'a \<times> 'b \<Rightarrow> 'b \<times> 'a" where
  "swap (x, y) = (y, x)"


export_code swap in Rust

end