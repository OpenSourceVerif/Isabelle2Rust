theory LetBindings_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Let_Binding_Test"


definition test_let :: "nat \<Rightarrow> nat" where
"test_let n \<equiv> (
   let x = n + 1 
   in x * 2
 )"

subsection "From Let_Case_Test"


fun add1 :: "int \<Rightarrow> int" where
  "add1 x = (let z = 1 in case z of y \<Rightarrow> (y+z))"

subsection "From Let_Nested_Test"


fun own:: "int \<Rightarrow> int" where
" 
own x = 
  (let y = 1 in 
    let z = y + 1 in
     let y = z + 1 in
      z
  )
"

export_code
  test_let add1 own
  in Rust

end
