theory Mut_Tree_Complex_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code mtree_any_label mtree_rebuild_chain mtree_interleaved_chain
            mtree_branch_rhs_chain mtree_two_chains
            mtree_saved_value_blocks_chain
  in Rust

end
