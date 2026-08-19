theory Type_Test
  imports Main "Rust.Rust_Base_Setup"
begin

hide_type (open) list
hide_const (open) Nil Cons

datatype 'a list =
    Nil
  | Cons (head: 'a) (tail: "'a list")

export_code Nil Cons in Rust

end
