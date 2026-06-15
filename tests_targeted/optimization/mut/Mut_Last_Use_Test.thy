theory Mut_Last_Use_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code lu_pair lu_triple lu_second_arg_last_use lu_chain_then_pair
  in Rust

end
