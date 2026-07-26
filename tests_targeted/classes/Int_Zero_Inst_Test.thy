theory Int_Zero_Inst_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* `0::int` is registered as a code_datatype constructor for int
   (`code_datatype "0::int" Pos Neg` in HOL/Int.thy), so Isabelle generates NO
   `zero_int_inst.zero_int` function -- zero is the constructor `Int::ZeroInta`.
   `one::int`, by contrast, has a real code equation (`1 = Pos Num.One`).

   A polymorphic `zero_neq_one` consumer instantiated at int therefore needs a
   reconstructed `impl Zero for Int` whose `zero()` returns the constructor, not
   a `panic!` stub. `of_bool :: bool => 'a::zero_neq_one` is exactly such a
   consumer; keeping it behind a polymorphic helper forces the trait-method
   dispatch `Int::zero()` / `Int::one()` rather than inlining. *)

definition pick :: "bool \<Rightarrow> 'a::zero_neq_one" where
  "pick b = of_bool b"

definition pick_int :: "bool \<Rightarrow> int" where
  "pick_int b = pick b"

export_code pick_int in Rust

end
