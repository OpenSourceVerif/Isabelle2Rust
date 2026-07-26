theory Mut_Chain_Unit_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Unit tests for mut-chain recognition.

   The positive cases mirror the M-Shadow/M-Mut shape from the paper:
   a source-level shadowed binding chain should become a generated handoff
   chain where each old value is used to produce the next one.

   The final case is a guard case: saving the old value before the update
   makes the previous binding live outside the handoff, so it should not be
   collapsed into a single mutable variable by a conservative mut pass. *)

datatype mut_color =
    MRed
  | MGreen
  | MBlue

fun color_next :: "mut_color \<Rightarrow> mut_color" where
  "color_next MRed = MGreen"
| "color_next MGreen = MBlue"
| "color_next MBlue = MRed"

fun color_tint :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
  "color_tint True c = c"
| "color_tint False c = color_next c"

fun color_step :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
  "color_step flag c = color_tint flag (color_next c)"

(* Adjacent shadowing chain: the minimal non-nat unit case. *)
definition color_adjacent_chain :: "mut_color \<Rightarrow> mut_color" where
"color_adjacent_chain c =
  (let x = c in
   let x = color_next x in
   let x = color_tint True x in
   x)"

(* Interleaved independent let-bindings should not break the mut chain. *)
definition color_interleaved_chain :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
"color_interleaved_chain seed c =
  (let x = c in
   let flag = seed in
   let x = color_tint flag x in
   let flag = (\<not> flag) in
   let x = color_tint flag (color_next x) in
   x)"

(* Non-trivial right-hand sides: the handoff is through helper calls. *)
definition color_call_rhs_chain :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
"color_call_rhs_chain flag c =
  (let x = c in
   let x = color_step flag x in
   let x = color_step (\<not> flag) x in
   x)"

(* Guard case: the old value escapes the handoff through saved. *)
definition color_saved_value_blocks_chain ::
  "mut_color \<Rightarrow> mut_color \<times> mut_color" where
"color_saved_value_blocks_chain c =
  (let x = c in
   let saved = x in
   let x = color_next x in
   (saved, x))"

export_code color_adjacent_chain color_interleaved_chain
            color_call_rhs_chain color_saved_value_blocks_chain
  in Rust

end
