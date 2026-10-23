theory Direct_Skew_Heap
  imports "Skew_Heap.Skew_Heap" "Rust.Rust_BigInt_Setup"
begin

definition merge_integer :: "integer tree \<Rightarrow> integer tree \<Rightarrow> integer tree" where
  "merge_integer a b = Skew_Heap.merge a b"

export_code merge_integer Leaf Node in OCaml
  module_name Reference file_prefix reference

export_code Skew_Heap.merge Leaf Node in Rust
  module_name Reference file_prefix reference

end
