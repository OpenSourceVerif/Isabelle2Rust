theory Mutability_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Mut_Chain_Test"


text \<open>
  Self-contained mut-chain example for the mutability-inference pass.

  The shadowed let-bindings of \<open>x\<close> form a handoff chain that Thingol prints as
  the distinct variables \<open>x\<close>, \<open>xa\<close>, \<open>xb\<close>, \<open>xc\<close> joined by \<open>.clone()\<close> hand-offs.
  The right-hand sides mix a constructor (\<open>S x\<close>) and a helper call (\<open>bump x\<close>),
  showing that the pass is agnostic to what each step computes.  The mut pass
  collapses the chain into a single \<open>let mut x\<close> updated by assignment and drops
  the now-redundant handoff clones.

  Using a custom recursive datatype (rather than \<open>nat\<close>) keeps the export to a
  single module, so it compiles end-to-end without the \<open>nat_of_integer\<close>/
  \<open>Orderings.Ord\<close> machinery that blocks Mut_Nat_Test.thy at stage1.
\<close>

datatype peano = Z | S peano

fun bump :: "peano \<Rightarrow> peano" where
  "bump n = S (S n)"

definition grow :: "peano \<Rightarrow> peano" where
  "grow n =
    (let x = n in
     let x = S x in
     let x = bump x in
     let x = S x in
     x)"

subsection "From Mut_Chain_Unit_Test"


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

subsection "From Mut_Generic_Wrapper_Test"


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

subsection "From Mut_Last_Use_Test"


(* Unit tests for M-LastUse.

   These cases exercise last-use clone elimination independently of a mut
   chain.  The tree type is recursive and therefore remains Clone-only, so
   duplicate uses produce visible clone calls in baseline Rust. *)

datatype lu_tree =
    LULeaf bool
  | LUNode lu_tree lu_tree

fun lu_flip :: "lu_tree \<Rightarrow> lu_tree" where
  "lu_flip (LULeaf b) = LULeaf (\<not> b)"
| "lu_flip (LUNode l r) = LUNode (lu_flip l) (lu_flip r)"

fun lu_wrap :: "lu_tree \<Rightarrow> lu_tree" where
  "lu_wrap t = LUNode (LULeaf True) t"

fun lu_pair :: "lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
  "lu_pair t = (t, t)"

fun lu_triple :: "lu_tree \<Rightarrow> lu_tree \<times> (lu_tree \<times> lu_tree)" where
  "lu_triple t = (t, (t, t))"

fun lu_pair2 :: "lu_tree \<Rightarrow> lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
  "lu_pair2 l r = (l, r)"

(* General last-use shape: f(x.clone(), x.clone()) with no later use of x. *)
definition lu_second_arg_last_use :: "lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
"lu_second_arg_last_use t = lu_pair2 t t"

(* Last-use after a short handoff chain. *)
definition lu_chain_then_pair :: "lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
"lu_chain_then_pair t =
  (let x = t in
   let x = lu_wrap x in
   let x = lu_flip x in
   lu_pair x)"

subsection "From Mut_Nat_Test"



definition let_mut_nat :: "nat \<Rightarrow> nat" where
"let_mut_nat n =
  (let x = n in
   let x = x + 1 in
   let x = x * 2 in
   x)"

subsection "From Mut_Tree_Complex_Test"


(* Complex mut-chain tests inspired by the recursive tree cases in the
   borrow/copy suites.

   The pass should be insensitive to what each right-hand side computes:
   recursive calls, constructors, and branch-local computation are all fine
   as long as the binding structure remains a local handoff chain.  The final
   saved-value case is a negative case where an older value remains live. *)

datatype mut_tree =
    MTLeaf bool
  | MTNode mut_tree mut_tree

fun mtree_any_label :: "mut_tree \<Rightarrow> bool" where
  "mtree_any_label (MTLeaf b) = b"
| "mtree_any_label (MTNode l r) =
     (mtree_any_label l \<or> mtree_any_label r)"

fun mtree_flip_labels :: "mut_tree \<Rightarrow> mut_tree" where
  "mtree_flip_labels (MTLeaf b) = MTLeaf (\<not> b)"
| "mtree_flip_labels (MTNode l r) =
     MTNode (mtree_flip_labels l) (mtree_flip_labels r)"

fun mtree_mirror :: "mut_tree \<Rightarrow> mut_tree" where
  "mtree_mirror (MTLeaf b) = MTLeaf b"
| "mtree_mirror (MTNode l r) =
     MTNode (mtree_mirror r) (mtree_mirror l)"

fun mtree_set_all :: "bool \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
  "mtree_set_all b (MTLeaf _) = MTLeaf b"
| "mtree_set_all b (MTNode l r) =
     MTNode (mtree_set_all b l) (mtree_set_all b r)"

(* Recursive rebuild chain: each RHS is a non-trivial tree transformation. *)
definition mtree_rebuild_chain :: "mut_tree \<Rightarrow> mut_tree" where
"mtree_rebuild_chain t =
  (let x = t in
   let x = mtree_flip_labels x in
   let x = mtree_mirror x in
   let x = mtree_set_all True x in
   x)"

(* Interleaved independent bindings and helper calls. *)
definition mtree_interleaved_chain :: "bool \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
"mtree_interleaved_chain seed t =
  (let x = t in
   let mark = seed in
   let x = mtree_set_all mark x in
   let mark = (\<not> mark) in
   let x = mtree_set_all mark (mtree_mirror x) in
   x)"

(* Branch-local rebuild: only one branch executes, but both compute a next x. *)
definition mtree_branch_rhs_chain :: "bool \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
"mtree_branch_rhs_chain flag t =
  (let x = t in
   let x = (if flag then mtree_mirror x else mtree_flip_labels x) in
   let x = mtree_set_all flag x in
   x)"

(* Two independent shadowing chains in the same expression. *)
definition mtree_two_chains ::
  "mut_tree \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
"mtree_two_chains t u =
  (let x = t in
   let y = u in
   let x = mtree_mirror x in
   let y = mtree_flip_labels y in
   MTNode x y)"

(* Guard case: saved keeps the older value live after the handoff point. *)
definition mtree_saved_value_blocks_chain ::
  "mut_tree \<Rightarrow> mut_tree" where
"mtree_saved_value_blocks_chain t =
  (let x = t in
   let saved = x in
   let x = mtree_mirror x in
   MTNode saved x)"

export_code
  grow color_adjacent_chain color_interleaved_chain color_call_rhs_chain
  color_saved_value_blocks_chain wrap_chain nested_wrap_chain pair_box_chain
  wrap_chain_then_dup wrap_saved_value_blocks_chain lu_pair lu_triple
  lu_second_arg_last_use lu_chain_then_pair let_mut_nat mtree_any_label
  mtree_rebuild_chain mtree_interleaved_chain mtree_branch_rhs_chain mtree_two_chains
  mtree_saved_value_blocks_chain
  in Rust

end
