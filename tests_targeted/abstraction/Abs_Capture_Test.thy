theory Abs_Capture_Test
  imports Main "Rust.Rust_Base_Setup"
begin


definition closure_1 where
" closure_1 = (let y::int = 1 in
                let f = (\<lambda>x. x + y) in
                
                let j = (\<lambda>x. x + y) in
                   let z :: int = y in
                  f 2)
"

export_code closure_1 in Rust


definition make_pair :: "int \<Rightarrow> (int \<Rightarrow> int) \<times> int" where
"make_pair y = ((\<lambda>x. x + y), y)"

export_code make_pair in Rust

end
