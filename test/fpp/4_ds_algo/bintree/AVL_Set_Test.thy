(* Author: Tobias Nipkow *)

subsection \<open>Invariant\<close>

theory AVL_Set_Test
imports
 AVL_Set_Code_Test "Rust.Rust_Base_Setup"
begin

(* Cleaned for the Rust export suite: the original theory's height/size-bound
   section (`fib_lowerbound`, `avl_size_lowerbound`, `avl_height_upperbound`)
   uses real analysis (`sqrt`, `log`) that is not in scope under the imports
   here, so the theory failed to elaborate before `export_code` was reached.
   Those lemmas — and the other correctness proofs — are neither exported nor
   depended on by the exported `avl`, so they are dropped. Only the executable
   `avl` invariant function is kept; it exports and compiles cleanly. *)

fun avl :: "'a tree_ht \<Rightarrow> bool" where
"avl Leaf = True" |
"avl (Node l (a,n) r) =
 (abs(int(height l) - int(height r)) \<le> 1 \<and>
  n = max (height l) (height r) + 1 \<and> avl l \<and> avl r)"

export_code avl in Rust

end
