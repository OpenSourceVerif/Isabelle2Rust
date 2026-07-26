theory MutChains_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Adjacent shadowed bindings form local mutable handoff chains. *)

datatype peano =
    Z
  | S peano

fun bump :: "peano \<Rightarrow> peano" where
  "bump n = S (S n)"

definition grow :: "peano \<Rightarrow> peano" where
  "grow n =
    (let x = n;
         x = S x;
         x = bump x;
         x = S x
     in x)"

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

definition color_adjacent_chain :: "mut_color \<Rightarrow> mut_color" where
  "color_adjacent_chain c =
    (let x = c;
         x = color_next x;
         x = color_tint True x
     in x)"

definition color_interleaved_chain :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
  "color_interleaved_chain seed c =
    (let x = c;
         flag = seed;
         x = color_tint flag x;
         flag = (\<not> flag);
         x = color_tint flag (color_next x)
     in x)"

definition color_call_rhs_chain :: "bool \<Rightarrow> mut_color \<Rightarrow> mut_color" where
  "color_call_rhs_chain flag c =
    (let x = c;
         x = color_step flag x;
         x = color_step (\<not> flag) x
     in x)"

(* Saving the old binding is the negative chain case. *)

definition color_saved_value_blocks_chain ::
  "mut_color \<Rightarrow> mut_color \<times> mut_color" where
  "color_saved_value_blocks_chain c =
    (let x = c;
         saved = x;
         x = color_next x
     in (saved, x))"

(* Generic wrappers exercise the same handoff with type parameters. *)

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
  "pair_box_keep_left (MutPairBox x _) = MutPairBox x x"

definition wrap_chain :: "'a mut_wrap \<Rightarrow> 'a mut_wrap" where
  "wrap_chain w =
    (let x = w;
         x = wrap_rebuild x;
         x = wrap_rebuild x
     in x)"

definition nested_wrap_chain ::
  "'a mut_wrap mut_wrap \<Rightarrow> 'a mut_wrap mut_wrap" where
  "nested_wrap_chain w =
    (let x = w;
         x = wrap_rebuild x;
         x = wrap_rebuild x
     in x)"

definition pair_box_chain :: "'a mut_pair_box \<Rightarrow> 'a mut_pair_box" where
  "pair_box_chain p =
    (let x = p;
         x = pair_box_swap x;
         x = pair_box_keep_left x
     in x)"

definition wrap_chain_then_dup ::
  "'a mut_wrap \<Rightarrow> 'a mut_wrap \<times> 'a mut_wrap" where
  "wrap_chain_then_dup w =
    (let x = w;
         x = wrap_rebuild x
     in wrap_dup x)"

definition wrap_saved_value_blocks_chain ::
  "'a mut_wrap \<Rightarrow> 'a mut_wrap \<times> 'a mut_wrap" where
  "wrap_saved_value_blocks_chain w =
    (let x = w;
         saved = x;
         x = wrap_rebuild x
     in (saved, x))"

definition let_mut_nat :: "nat \<Rightarrow> nat" where
  "let_mut_nat n =
    (let x = n;
         x = x + 1;
         x = x * 2
     in x)"

export_code
  grow color_adjacent_chain color_interleaved_chain color_call_rhs_chain
  color_saved_value_blocks_chain wrap_chain nested_wrap_chain pair_box_chain
  wrap_chain_then_dup wrap_saved_value_blocks_chain let_mut_nat
  in Rust

end
