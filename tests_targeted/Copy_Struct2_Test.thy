theory Copy_Struct2_Test
  imports Main "Rust.Rust_Setup"
begin

datatype color =
    Red
  | Green
  | Blue

fun is_red :: "color \<Rightarrow> bool" where
  "is_red Red = True"
| "is_red Green = False"
| "is_red Blue = False"

datatype pixel =
  Pixel color color color

fun get_first_color :: "pixel \<Rightarrow> color" where
  "get_first_color (Pixel r g b) = r"

fun rotate_pixel :: "pixel \<Rightarrow> pixel" where
  "rotate_pixel (Pixel r g b) = Pixel g b r"


fun replace_first_color :: "pixel \<Rightarrow> color \<Rightarrow> pixel" where
  "replace_first_color (Pixel r g b) c = Pixel c g b"

export_code is_red get_first_color rotate_pixel replace_first_color in Rust

end