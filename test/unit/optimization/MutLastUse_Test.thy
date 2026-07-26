theory MutLastUse_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* A recursive non-Copy tree keeps last-use clone elimination observable. *)

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

(* The final clone may move through call arguments or a short chain. *)

definition lu_second_arg_last_use :: "lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
  "lu_second_arg_last_use t = lu_pair2 t t"

definition lu_chain_then_pair :: "lu_tree \<Rightarrow> lu_tree \<times> lu_tree" where
  "lu_chain_then_pair t =
    (let x = t;
         x = lu_wrap x;
         x = lu_flip x
     in lu_pair x)"

export_code
  lu_pair lu_triple lu_second_arg_last_use lu_chain_then_pair
  in Rust

end
