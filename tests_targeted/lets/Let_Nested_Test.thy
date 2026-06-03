theory Let_Nested_Test
  imports Main "Rust.Rust_Setup"
begin

fun own:: "int \<Rightarrow> int" where
" 
own x = 
  (let y = 1 in 
    let z = y + 1 in
     let y = z + 1 in
      z
  )
"

export_code  own in Rust

end