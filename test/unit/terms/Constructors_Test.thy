theory Constructors_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Cons_As_Value_Test"


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

subsection "From Cons_Mono_Test"



definition c :: int where "c \<equiv> 42"

subsection "From Cons_Poly_Test"



definition zero :: "'a::zero" where "zero \<equiv> 0"  

subsection "From Result_Test"


datatype ('a, 'b) result = Ok 'a | Err 'b

fun is_ok :: "('a, 'b) result \<Rightarrow> bool" where
  "is_ok (Ok x) = True"
| "is_ok (Err e) = False"

fun is_err :: "('a, 'b) result \<Rightarrow> bool" where
  "is_err (Ok x) = False"
| "is_err (Err e) = True"

fun get_or :: "('a, 'b) result \<Rightarrow> 'a \<Rightarrow> 'a" where
  "get_or (Ok x) d = x"
| "get_or (Err e) d = d"

fun err_or :: "('a, 'b) result \<Rightarrow> 'b \<Rightarrow> 'b" where
  "err_or (Ok x) d = d"
| "err_or (Err e) d = e"

fun swap_result :: "('a, 'b) result \<Rightarrow> ('b, 'a) result" where
  "swap_result (Ok x) = Err x"
| "swap_result (Err e) = Ok e"

fun choose_first_ok :: "('a, 'b) result \<Rightarrow> ('a, 'b) result \<Rightarrow> ('a, 'b) result" where
  "choose_first_ok (Ok x) y = Ok x"
| "choose_first_ok (Err e) y = y"

fun flatten_result :: "(('a, 'b) result, 'b) result \<Rightarrow> ('a, 'b) result" where
  "flatten_result (Ok r) = r"
| "flatten_result (Err e) = Err e"

export_code
  wrap_bit0 wrap_bit1 c zero is_ok is_err get_or err_or swap_result choose_first_ok
  flatten_result
  in Rust

end
