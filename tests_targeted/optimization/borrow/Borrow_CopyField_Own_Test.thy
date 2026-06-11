theory Borrow_CopyField_Own_Test
  imports Main "Rust.Rust_Setup"
begin

(* ── Unit test: extracting Copy-typed fields does not block borrow inference ──
   When a non-Copy parameter is matched and a Copy-typed field is used in an
   owned position (e.g., returned or put in a constructor), the borrow pass
   classifies this as  Own(CopyUse)  – a demand that is compatible with shared
   borrowing (the value can be copied from a & reference).

   This contrasts with using a non-Copy field without .clone() (Move demand).

   After the copy pass, fields of Copy types (bool, user-defined Copy enums)
   are known to be Copy, so the borrow pass can apply the  Own(CopyUse) rule.  *)

(* Recursive tree: non-Copy.  Leaf carries a bool (Copy) label.              *)
datatype ce_tree =
    CELeaf bool
  | CENode ce_tree ce_tree

(* Wrapper holding a bool (Copy) and a ce_tree (non-Copy).                   *)
datatype ce_holder =
  CEHolder bool ce_tree

(* Returns a Copy bool field extracted from the non-Copy tree.
   In the baseline: `b.clone()`.  Copy-field use → Own(CopyUse) → borrowable. *)
fun ce_leaf_val :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_val (CELeaf b) = b"
| "ce_leaf_val (CENode _ _) = False"

(* Returns the bool (Copy) flag from the holder.
   The ce_tree sub-field is never touched → Obs on the holder param overall.  *)
fun ce_holder_flag :: "ce_holder \<Rightarrow> bool" where
  "ce_holder_flag (CEHolder b _) = b"

(* Uses the bool field in a new bool expression (still Copy use) → borrowable *)
fun ce_leaf_negated :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_negated (CELeaf b) = (\<not> b)"
| "ce_leaf_negated (CENode _ _) = True"

(* Observational depth-check: returns bool, never moves tree → borrowable *)
fun ce_is_single_leaf :: "ce_tree \<Rightarrow> bool" where
  "ce_is_single_leaf (CELeaf _) = True"
| "ce_is_single_leaf (CENode (CELeaf _) (CELeaf _)) = True"
| "ce_is_single_leaf _ = False"

export_code ce_leaf_val ce_holder_flag ce_leaf_negated ce_is_single_leaf
  in Rust

end
