theory Copy_Struct_Test
  imports Main "Rust.Rust_Setup"
begin

datatype flag_pair =
  FlagPair bool bool

fun get_left :: "flag_pair \<Rightarrow> bool" where
  "get_left (FlagPair x y) = x"

fun get_right :: "flag_pair \<Rightarrow> bool" where
  "get_right (FlagPair x y) = y"

fun swap_flag_pair :: "flag_pair \<Rightarrow> flag_pair" where
  "swap_flag_pair (FlagPair x y) = FlagPair y x"

export_code get_left get_right swap_flag_pair in Rust

end