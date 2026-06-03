theory Type_Func_Mono_Test
  imports   
    Main "Rust.Rust_Setup"
begin

fun apply_twice2 :: "(int \<Rightarrow> int) \<Rightarrow> int \<Rightarrow> int" where
  "apply_twice2 f x = f (f x)"

export_code apply_twice2 in Rust
                     
end