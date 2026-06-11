theory Copy_Recursive_NonCopy_Test
  imports Main "Rust.Rust_Setup"
begin

(* ── Unit test: non-Copy fields stop Copy propagation upward ─────────────────
   copy_tree is recursive (BNode stores Box<CopyTree>) → non-Copy.
   Any type that contains copy_tree as a field is also non-Copy, even if all
   other fields are bool (Copy).  The copy pass must not infer Copy for such
   compound types.

   At the same time, types that only contain Copy fields (bool, other Copy
   user-defined types) SHOULD be promoted to Copy.                            *)

(* Recursive → non-Copy regardless of field types *)
datatype small_tree =
    SLeaf bool
  | SNode small_tree small_tree

(* Wraps a non-Copy tree → must stay non-Copy *)
datatype tree_holder =
  TreeHolder small_tree bool

(* Wraps only bool fields → SHOULD become Copy *)
datatype flag_holder =
  FlagHolder bool bool

(* Generic wrapper: Copy only when 'a is Copy *)
datatype 'a opt_val =
    OptNone
  | OptSome 'a

(* flag_holder is Copy → opt_val<flag_holder> SHOULD be Copy *)
(* small_tree is non-Copy → opt_val<small_tree> must stay non-Copy *)

fun stree_is_leaf :: "small_tree \<Rightarrow> bool" where
  "stree_is_leaf (SLeaf _) = True"
| "stree_is_leaf (SNode _ _) = False"

fun stree_dup :: "small_tree \<Rightarrow> small_tree \<times> small_tree" where
  "stree_dup x = (x, x)"

fun holder_flag :: "tree_holder \<Rightarrow> bool" where
  "holder_flag (TreeHolder _ b) = b"

fun holder_dup :: "tree_holder \<Rightarrow> tree_holder \<times> tree_holder" where
  "holder_dup x = (x, x)"

fun flag_holder_dup :: "flag_holder \<Rightarrow> flag_holder \<times> flag_holder" where
  "flag_holder_dup x = (x, x)"

fun opt_val_has :: "'a opt_val \<Rightarrow> bool" where
  "opt_val_has OptNone = False"
| "opt_val_has (OptSome _) = True"

fun opt_val_dup :: "'a opt_val \<Rightarrow> 'a opt_val \<times> 'a opt_val" where
  "opt_val_dup x = (x, x)"

fun flag_holder_opt_dup :: "flag_holder opt_val \<Rightarrow> flag_holder opt_val \<times> flag_holder opt_val" where
  "flag_holder_opt_dup x = opt_val_dup x"

export_code stree_is_leaf stree_dup
            holder_flag holder_dup
            flag_holder_dup
            opt_val_has opt_val_dup
            flag_holder_opt_dup
  in Rust

end
