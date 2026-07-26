theory Borrow_Per_Param_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* ── Unit test: per-parameter borrowability in multi-argument functions ───────
   The borrow pass analyses each parameter independently.  A function with
   mixed demands across its parameters should get a  _borrow  variant where
   only the borrowable positions are changed to  &T.

   Scenarios here:
     • one param observed-only, another returned directly (Move) → first
       position is borrowable, second is not
     • two params both observed → both borrowable
     • one param moved into a constructor, other param observed → second
       borrowable, first not
     • bool param (Copy) is never a borrow candidate (already cheap to pass)  *)

datatype mp_tree =
    MPLeaf bool
  | MPNode mp_tree mp_tree

(* both params are returned directly (Move) → neither is borrowable *)
fun mp_pair_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree \<times> mp_tree" where
  "mp_pair_return t u = (t, u)"

(* first param observed (→ borrowable), second returned directly (Move → not) *)
fun mp_check_or_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree" where
  "mp_check_or_return (MPLeaf _) u = u"
| "mp_check_or_return (MPNode _ _) u = u"

(* both params observed → both borrowable *)
fun mp_compare :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_compare (MPLeaf b1) (MPLeaf b2) = (b1 = b2)"
| "mp_compare (MPLeaf _) (MPNode _ _) = False"
| "mp_compare (MPNode _ _) (MPLeaf _) = False"
| "mp_compare (MPNode _ _) (MPNode _ _) = True"

(* first param consumed into constructor (Move → not borrowable),
   second param only observed (→ borrowable) *)
fun mp_build_and_check :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_build_and_check t (MPLeaf b) = b"
| "mp_build_and_check t (MPNode _ _) = False"

(* bool param (Copy) is not a borrow candidate; mp_tree param is observed *)
fun mp_flag_and_observe :: "bool \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_flag_and_observe flag (MPLeaf b) = (flag \<and> b)"
| "mp_flag_and_observe flag (MPNode _ _) = flag"

export_code mp_pair_return mp_check_or_return mp_compare
            mp_build_and_check mp_flag_and_observe
  in Rust

end
