(* Regression test for code_rust.ML print_generic_prefix_typ:
   Calling a function whose first argument is a function-typed value with
   a class constraint used to crash export_code with a Match exception in
   fn_trait_impl_syntax (the "fun" tyco's custom syntax was invoked with
   zero args because print_generic_prefix_typ strips type arguments).
   This test exercises the path without forcing a concrete class instance,
   so it both reproduces the original failure and produces compilable Rust. *)

theory Fun_Upd_Test
  imports Main "Rust.Rust_Base_Setup"
begin

class my_cls =
  fixes my_op :: "'a \<Rightarrow> 'a"

definition apply_first :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "apply_first g x = g (my_op x)"

definition test_call :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "test_call f x = apply_first f x"

export_code test_call in Rust

end
