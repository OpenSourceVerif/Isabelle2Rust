theory Cons_As_Value_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* A unary constructor of a polymorphic-free datatype used as a first-class
   function value (passed to a higher-order function without being applied).
   The Rust backend eta-expands it into a closure; it must NOT be prefixed
   with the enum's `Tyco::` qualifier (regression for `Num::(move |a| ...)`). *)

datatype mynum = One | Bit0 mynum | Bit1 mynum

fun map_opt :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a option \<Rightarrow> 'b option" where
  "map_opt f None = None"
| "map_opt f (Some x) = Some (f x)"

definition wrap_bit0 :: "mynum option \<Rightarrow> mynum option" where
  "wrap_bit0 x = map_opt Bit0 x"

definition wrap_bit1 :: "mynum option \<Rightarrow> mynum option" where
  "wrap_bit1 x = map_opt Bit1 x"

export_code wrap_bit0 wrap_bit1 in Rust

end
