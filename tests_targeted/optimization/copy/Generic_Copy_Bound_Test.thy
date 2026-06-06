theory Generic_Copy_Bound_Test
  imports Main "Rust.Rust_Setup"
begin

datatype 'a copy_wrap =
  CopyWrap 'a

fun duplicate :: "'a \<Rightarrow> 'a \<times> 'a" where
  "duplicate x = (x, x)"

fun duplicate_wrap :: "'a copy_wrap \<Rightarrow> 'a copy_wrap \<times> 'a copy_wrap" where
  "duplicate_wrap x = (x, x)"

export_code  duplicate_wrap in Rust

export_code duplicate duplicate_wrap in Rust

end
