theory Abs_Capture_Test
  imports Main "Rust.Rust_Setup"
begin


definition closure_1 where
" closure_1 = (let y::int = 1 in
                let f = (\<lambda>x. x + y) in
                  f 2)
"

export_code closure_1 in Rust

end
