theory Color_Dup_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype color =
    Red
  | Green
  | Blue

fun color_dup :: "color \<Rightarrow> color \<times> color" where
  "color_dup c = (c, c)"

export_code color_dup in Rust

end
