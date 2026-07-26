theory Mut_Generic_Wrapper_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Generic wrapper tests for mut-chain and last-use behavior.

   These mirror the generic wrapper style used by copy/borrow tests.  The
   chain type stays fixed across every update, so a future mut pass can use
   the same mutable variable without changing its Rust type. *)

datatype 'a mut_wrap =
  MutWrap 'a

datatype 'a mut_pair_box =
  MutPairBox 'a 'a

fun wrap_rebuild :: "'a mut_wrap \<Rightarrow> 'a mut_wrap" where
  "wrap_rebuild (MutWrap x) = MutWrap x"

fun wrap_dup :: "'a mut_wrap \<Rightarrow> 'a mut_wrap \<times> 'a mut_wrap" where
  "wrap_dup x = (x, x)"

fun pair_box_swap :: "'a mut_pair_box \<Rightarrow> 'a mut_pair_box" where
  "pair_box_swap (MutPairBox x y) = MutPairBox y x"

fun pair_box_keep_left :: "'a mut_pair_box \<Rightarrow> 'a mut_pair_box" where
  "pair_box_keep_left (MutPairBox x y) = MutPairBox x x"

definition wrap_chain :: "'a mut_wrap \<Rightarrow> 'a mut_wrap" where
"wrap_chain w =
  (let x = w in
   let x = wrap_rebuild x in
   let x = wrap_rebuild x in
   x)"

definition nested_wrap_chain ::
  "'a mut_wrap mut_wrap \<Rightarrow> 'a mut_wrap mut_wrap" where
"nested_wrap_chain w =
  (let x = w in
   let x = wrap_rebuild x in
   let x = wrap_rebuild x in
   x)"

definition pair_box_chain ::
  "'a mut_pair_box \<Rightarrow> 'a mut_pair_box" where
"pair_box_chain p =
  (let x = p in
   let x = pair_box_swap x in
   let x = pair_box_keep_left x in
   x)"

definition wrap_chain_then_dup ::
  "'a mut_wrap \<Rightarrow> 'a mut_wrap \<times> 'a mut_wrap" where
"wrap_chain_then_dup w =
  (let x = w in
   let x = wrap_rebuild x in
   wrap_dup x)"

(* Guard case: the saved binding keeps the old wrapper live. *)
definition wrap_saved_value_blocks_chain ::
  "'a mut_wrap \<Rightarrow> 'a mut_wrap \<times> 'a mut_wrap" where
"wrap_saved_value_blocks_chain w =
  (let x = w in
   let saved = x in
   let x = wrap_rebuild x in
   (saved, x))"

export_code wrap_chain nested_wrap_chain pair_box_chain
            wrap_chain_then_dup wrap_saved_value_blocks_chain
  in Rust

end
