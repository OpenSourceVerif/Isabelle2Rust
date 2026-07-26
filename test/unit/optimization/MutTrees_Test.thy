theory MutTrees_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Tree rebuilds exercise non-trivial right-hand sides in mut chains. *)

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

definition mtree_rebuild_chain :: "mut_tree \<Rightarrow> mut_tree" where
  "mtree_rebuild_chain t =
    (let x = t;
         x = mtree_flip_labels x;
         x = mtree_mirror x;
         x = mtree_set_all True x
     in x)"

definition mtree_interleaved_chain :: "bool \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
  "mtree_interleaved_chain seed t =
    (let x = t;
         mark = seed;
         x = mtree_set_all mark x;
         mark = (\<not> mark);
         x = mtree_set_all mark (mtree_mirror x)
     in x)"

definition mtree_branch_rhs_chain :: "bool \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
  "mtree_branch_rhs_chain flag t =
    (let x = t;
         x = (if flag then mtree_mirror x else mtree_flip_labels x);
         x = mtree_set_all flag x
     in x)"

definition mtree_two_chains ::
  "mut_tree \<Rightarrow> mut_tree \<Rightarrow> mut_tree" where
  "mtree_two_chains t u =
    (let x = t;
         y = u;
         x = mtree_mirror x;
         y = mtree_flip_labels y
     in MTNode x y)"

(* Saving the old tree prevents an unsafe handoff collapse. *)

definition mtree_saved_value_blocks_chain :: "mut_tree \<Rightarrow> mut_tree" where
  "mtree_saved_value_blocks_chain t =
    (let x = t;
         saved = x;
         x = mtree_mirror x
     in MTNode saved x)"

export_code
  mtree_any_label mtree_rebuild_chain mtree_interleaved_chain
  mtree_branch_rhs_chain mtree_two_chains mtree_saved_value_blocks_chain
  in Rust

end
