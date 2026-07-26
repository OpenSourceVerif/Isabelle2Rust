theory List_Ops_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* ── Complex test: custom list type exercising both copy and borrow passes ────
   MyList is a recursive type → stays non-Copy after the copy pass.
   bool elements are Copy, so Copy-field uses in functions are Own(CopyUse).

   Expected outcomes after both passes:
     Copy pass:
       • MyList stays Clone-only (recursive with Box)
       • bool stays Copy (primitive)
       • Standalone bool functions get no _copy specialisation (already concrete)

     Borrow pass:
       • list_is_empty:  observational only → borrowable
       • list_head:      returns Copy bool  → Own(CopyUse), borrowable
       • list_length:    recursive, returns Nat (non-Copy constructed value, not
                         the param itself) → fixed-point analysis makes it
                         borrowable via B-Recursive
       • list_any_true:  recursive observation, returns bool → borrowable
       • list_append:    first param is recursively traversed (borrowable);
                         second param is returned directly in the base case
                         (Move demand) → second param NOT borrowable
       • list_dup:       param returned in both slots of the pair → Move → NOT
                         borrowable                                             *)

datatype 'a my_list =
    MyNil
  | MyCons 'a "'a my_list"

(* ── Observational (always borrowable) ──────────────────────────────────────*)

fun list_is_empty :: "'a my_list \<Rightarrow> bool" where
  "list_is_empty MyNil = True"
| "list_is_empty (MyCons _ _) = False"

(* returns a Copy bool from the head → Own(CopyUse) demand → borrowable *)
fun list_head :: "bool my_list \<Rightarrow> bool" where
  "list_head MyNil = False"
| "list_head (MyCons x _) = x"

(* ── Recursive observation (borrowable via B-Recursive fixed-point) ──────── *)

fun list_length :: "'a my_list \<Rightarrow> nat" where
  "list_length MyNil = 0"
| "list_length (MyCons _ xs) = Suc (list_length xs)"

fun list_any_true :: "bool my_list \<Rightarrow> bool" where
  "list_any_true MyNil = False"
| "list_any_true (MyCons x xs) = (x \<or> list_any_true xs)"

fun list_all_true :: "bool my_list \<Rightarrow> bool" where
  "list_all_true MyNil = True"
| "list_all_true (MyCons x xs) = (x \<and> list_all_true xs)"

(* ── Mixed borrowability: first param borrowable, second NOT ─────────────── *)

(* first param is recursively traversed; second param is returned directly in
   the base case → second param has Move demand                               *)
fun list_append :: "'a my_list \<Rightarrow> 'a my_list \<Rightarrow> 'a my_list" where
  "list_append MyNil ys = ys"
| "list_append (MyCons x xs) ys = MyCons x (list_append xs ys)"

(* ── Not borrowable: direct return of parameter ─────────────────────────────*)

fun list_dup :: "'a my_list \<Rightarrow> 'a my_list \<times> 'a my_list" where
  "list_dup xs = (xs, xs)"

export_code list_is_empty list_head list_length list_any_true list_all_true
            list_append list_dup
  in Rust

end
