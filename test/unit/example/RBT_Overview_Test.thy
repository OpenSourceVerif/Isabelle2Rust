theory RBT_Overview_Test
  imports "HOL-Library.RBT_Impl" "Rust.Rust_Base_Setup"
begin

text \<open>
  Running example used in the overview of the Isabelle2Rust paper.
  The generated dependencies include the datatypes @{type RBT_Impl.color} and
  @{type RBT_Impl.rbt}, while the selected constants expose the recursive
  invariant check and its whole-tree caller.
\<close>

export_code RBT_Impl.inv1 RBT_Impl.is_rbt in Rust

end
