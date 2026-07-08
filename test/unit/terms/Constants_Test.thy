theory Constants_Test
  imports Main "Rust.Rust_Setup"
begin

datatype color = Red | Green | Blue | RGB int int int

datatype 'a slot = EmptySlot | Slot 'a

definition answer :: int where
  "answer = 42"

definition answer_id :: int where
  "answer_id = answer"

definition zero :: "'a::zero" where
  "zero \<equiv> 0"

definition red :: color where
  "red = Red"

definition rgb :: "int \<Rightarrow> color" where
  "rgb r = RGB r 0 0"

definition empty_slot :: "'a slot" where
  "empty_slot = EmptySlot"

definition empty_option :: "'a option" where
  "empty_option = None"

definition slot :: "'a \<Rightarrow> 'a slot" where
  "slot x = Slot x"

fun color_code :: "color \<Rightarrow> int" where
  "color_code Red = 0"
| "color_code Green = 1"
| "color_code Blue = 2"
| "color_code (RGB r _ _) = r"

fun slot_or :: "'a \<Rightarrow> 'a slot \<Rightarrow> 'a" where
  "slot_or d EmptySlot = d"
| "slot_or _ (Slot x) = x"

export_code
  answer answer_id zero red rgb empty_slot empty_option slot color_code slot_or
  in Rust

end
