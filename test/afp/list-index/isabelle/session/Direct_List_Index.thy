theory Direct_List_Index
  imports "List-Index.List_Index" "Rust.Rust_BigInt_Setup"
begin

definition last_index_integer :: "integer list \<Rightarrow> integer \<Rightarrow> integer" where
  "last_index_integer xs x = integer_of_nat (List_Index.last_index xs x)"

export_code last_index_integer in OCaml
  module_name Reference file_prefix reference

export_code List_Index.last_index in Rust
  module_name Reference file_prefix reference

end
