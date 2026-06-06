theory Type_Record_Test
  imports Main "Rust.Rust_Setup"
begin

record point = 
  Xcoord :: int
  Ycoord :: int

definition pt1 :: point where  "pt1 \<equiv> (| Xcoord = 999, Ycoord = 23 |)"

export_code pt1  in Rust

end
