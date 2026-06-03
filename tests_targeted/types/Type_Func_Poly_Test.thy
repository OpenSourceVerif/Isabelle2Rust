theory Type_Func_Poly_Test
  imports   
    Main "Rust.Rust_Setup"
begin

fun apply_twice :: "('a \<Rightarrow> 'a) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "apply_twice f x = f (f x)"

export_code apply_twice in Rust
                     
end