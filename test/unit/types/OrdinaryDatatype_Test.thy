theory OrdinaryDatatype_Test
  imports Main "Rust.Rust_Setup"
begin

datatype color = Red | Green | Blue | RGB int int int

fun color_code :: "color \<Rightarrow> int" where
  "color_code Red = 0"
| "color_code Green = 1"
| "color_code Blue = 2"
| "color_code (RGB r _ _) = r"

datatype 'a value_slot = Empty | Value 'a

fun value_or :: "'a \<Rightarrow> 'a value_slot \<Rightarrow> 'a" where
  "value_or d Empty = d"
| "value_or _ (Value x) = x"

fun map_slot :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a value_slot \<Rightarrow> 'b value_slot" where
  "map_slot _ Empty = Empty"
| "map_slot f (Value x) = Value (f x)"

datatype ('a, 'b) typed_choice = PickLeft 'a | PickRight 'b | PickBoth 'a 'b

fun swap_choice :: "('a, 'b) typed_choice \<Rightarrow> ('b, 'a) typed_choice" where
  "swap_choice (PickLeft x) = PickRight x"
| "swap_choice (PickRight y) = PickLeft y"
| "swap_choice (PickBoth x y) = PickBoth y x"

fun make_both :: "'a \<Rightarrow> 'b \<Rightarrow> ('a, 'b) typed_choice" where
  "make_both x y = PickBoth x y"

export_code
  color_code value_or map_slot swap_choice make_both
  in Rust

end
