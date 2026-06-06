theory Abs_No_Capture_Test
  imports Main "Rust.Rust_Setup"
begin


definition closure_2 where
"closure_2 =(\<lambda>x::int. x + 1) 10
"
export_code closure_2 in Rust

end
