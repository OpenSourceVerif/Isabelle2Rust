theory Name_Hygiene_Test
  imports "Rust.Rust_Base_Setup"
begin

(* Two irrefutable parameters whose intermediate values have the same Rust
   type: the first field x1 must not replace the second synthetic parameter. *)
datatype 'a single = Single 'a
fun direct_same_type :: "bool single single \<Rightarrow> bool single \<Rightarrow> bool single \<times> bool" where
  "direct_same_type (Single x1) (Single y) = (x1, y)"
definition direct_observe :: bool where
  "direct_observe = (snd (direct_same_type (Single (Single False)) (Single True)))"
lemma "direct_observe = True" by eval

(* Two pending Box scrutinees coexist after the outer constructor is matched.
   Inner matching must reserve the temporary names holding both subtrees. *)
datatype tree = Leaf bool | Node tree tree
fun frontier :: "tree \<Rightarrow> (tree \<times> tree \<times> tree \<times> tree) option" where
  "frontier (Node (Node a b) (Node c d)) = Some (a, b, c, d)"
| "frontier _ = None"
definition frontier_observe :: bool where
  "frontier_observe = (case frontier (Node (Node (Leaf False) (Leaf True)) (Node (Leaf True) (Leaf False))) of
      Some (Leaf False, Leaf True, Leaf True, Leaf False) \<Rightarrow> True
    | _ \<Rightarrow> False)"
lemma "frontier_observe = True" by eval

(* Automatic eta expansion must choose names fresh for explicit lambda
   binders as well as outer variables. The gate selects first vs second arg. *)
definition eta_shadow :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool) list" where
  "eta_shadow gate = [(\<lambda>eta_arg. if gate then (\<lambda>y. eta_arg) else (\<lambda>y. y))]"
definition eta_observe :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool" where
  "eta_observe gate a b = (hd (eta_shadow gate)) a b"
lemma "eta_observe True False True = False" by eval
lemma "eta_observe False False True = True" by eval

(* Positive controls exercise capture alias names and local let shadowing.
   The source binder x_cap must remain distinct from the captured x clone. *)
definition cap_safe :: "bool \<Rightarrow> (bool \<Rightarrow> bool) list" where
  "cap_safe x = [(\<lambda>x_cap. x \<and> x_cap)]"
definition cap_observe :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "cap_observe x y = (hd (cap_safe x)) y"
definition local_safe :: "bool \<times> bool \<Rightarrow> bool \<times> bool \<Rightarrow> bool" where
  "local_safe p q = (let (x1, p0) = p; (x1, p1) = q in (p0 \<and> x1) \<or> p1)"
lemma "cap_observe True False = False" by eval
lemma "local_safe (False, True) (True, False) = True" by eval


(* A partial equation keeps both nested Box frontiers in the same source row.
   Its input below is in the equation domain; undefined inputs are not tested. *)
fun frontier_partial :: "tree \<Rightarrow> tree \<times> tree \<times> tree \<times> tree" where
  "frontier_partial (Node (Node a b) (Node c d)) = (a, b, c, d)"
definition partial_observe :: bool where
  "partial_observe = (case frontier_partial (Node (Node (Leaf False) (Leaf True)) (Node (Leaf True) (Leaf False))) of
      (Leaf False, Leaf True, Leaf True, Leaf False) \<Rightarrow> True
    | _ \<Rightarrow> False)"
lemma "partial_observe = True" by eval

(* Alpha-renaming only the explicit lambda binder must preserve behavior. *)
definition eta_control :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool) list" where
  "eta_control gate = [(\<lambda>user_arg. if gate then (\<lambda>y. user_arg) else (\<lambda>y. y))]"
definition eta_control_observe :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool" where
  "eta_control_observe gate a b = (hd (eta_control gate)) a b"
lemma "eta_control_observe True False True = False" by eval


(* Source p0 forces the first outer Box temporary to be p0a. Inner matcher
   temporaries must still avoid p1, which holds the pending right subtree. *)
fun frontier_named :: "tree \<Rightarrow> tree \<times> tree \<times> tree \<times> tree" where
  "frontier_named (Node (Node p0 b) (Node c d)) = (p0, b, c, d)"
definition named_observe :: bool where
  "named_observe = (case frontier_named (Node (Node (Leaf False) (Leaf True)) (Node (Leaf True) (Leaf False))) of
      (Leaf False, Leaf True, Leaf True, Leaf False) \<Rightarrow> True
    | _ \<Rightarrow> False)"
lemma "named_observe = True" by eval

(* Depth-based temporary names must avoid all pending outer frontier columns,
   including p1 while the left subtree is being inspected recursively. *)
fun frontier_deep :: "tree \<Rightarrow> tree \<times> tree \<times> tree \<times> tree \<times> tree" where
  "frontier_deep (Node (Node (Node a b) c) (Node d e)) = (a, b, c, d, e)"
definition deep_observe :: bool where
  "deep_observe = (case frontier_deep (Node (Node (Node (Leaf False) (Leaf True)) (Leaf False)) (Node (Leaf True) (Leaf False))) of
      (Leaf False, Leaf True, Leaf False, Leaf True, Leaf False) \<Rightarrow> True
    | _ \<Rightarrow> False)"
lemma "deep_observe = True" by eval


(* Native True/False patterns below a Box must survive code adaptation and
   choose the matching equation. The False row returns the left subtree;
   losing the native constructors used to emit an unconditional panic. *)
fun cross_rows :: "tree \<Rightarrow> tree option" where
  "cross_rows (Node _ (Leaf True)) = None"
| "cross_rows (Node p0a (Leaf False)) = Some p0a"
| "cross_rows _ = None"
definition cross_observe :: bool where
  "cross_observe = (case cross_rows (Node (Leaf True) (Leaf False)) of
      Some (Leaf True) \<Rightarrow> True | _ \<Rightarrow> False)"
lemma "cross_observe = True" by eval


(* Unboxed source fields from later rows must be reserved when temporaries
   are allocated from the first row for another boxed field. Custom tags
   avoid the separate native-bool-pattern issue exercised by Cross_Rows. *)
datatype tag = On | Off
datatype mixed = Item tag | Mix bool mixed
fun cross_row_names :: "mixed \<Rightarrow> bool option" where
  "cross_row_names (Mix _ (Item On)) = None"
| "cross_row_names (Mix p0a (Item Off)) = Some p0a"
| "cross_row_names _ = None"
definition cross_names_observe :: bool where
  "cross_names_observe = (cross_row_names (Mix True (Item Off)) = Some True)"
lemma "cross_names_observe = True" by eval

(* A capture alias x_cap and explicit source parameter x_cap are made fresh
   by the existing capture-to-binder context propagation. *)
definition cap_named :: "bool \<Rightarrow> (bool \<Rightarrow> bool) list" where
  "cap_named x = [(\<lambda>x_cap. if x_cap then x else \<not> x)]"
definition cap_named_observe :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "cap_named_observe x y = (hd (cap_named x)) y"
lemma "cap_named_observe False False = True" by eval


(* Eta arguments distributed into case branches must also remain distinct
   from the branch pattern binders, which are absent from free-variable sets. *)
definition eta_case :: "bool \<Rightarrow> (bool option \<Rightarrow> bool \<Rightarrow> bool) list" where
  "eta_case gate = [(\<lambda>x. case x of None \<Rightarrow> (\<lambda>y. y)
     | Some eta_arg \<Rightarrow> (\<lambda>y. if gate then eta_arg else y))]"
definition eta_case_observe :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool" where
  "eta_case_observe gate a b = (hd (eta_case gate)) (Some a) b"
lemma "eta_case_observe False False True = True" by eval

(* Character equality exercises eight constructor fields and a second char
   parameter: all fields must be bound only after both arguments are read. *)
definition char_equal :: "char \<Rightarrow> char \<Rightarrow> bool" where
  "char_equal a b = (a = b)"
lemma "char_equal (Char False False False False False False False False)
                  (Char True False False False False False False False) = False" by eval

(* Keep input construction and calls to the functions under test in generated
   code, so Stage-2 can rewrite their calls together with borrowed signatures.
   The handwritten Rust tests use only nullary boolean entry points, shared by
   Stage-1 and Stage-2. Enumerate the same boolean inputs as the original tests. *)
definition all_bool_inputs :: "(bool \<Rightarrow> bool) \<Rightarrow> bool" where
  "all_bool_inputs predicate = (predicate False \<and> predicate True)"

definition check_direct_parameters :: bool where
  "check_direct_parameters = all_bool_inputs (\<lambda>a. all_bool_inputs (\<lambda>b.
    case direct_same_type (Single (Single a)) (Single b) of
      (Single x, y) \<Rightarrow> x = a \<and> y = b))"
lemma "check_direct_parameters = True" by eval

definition check_character_parameters :: bool where
  "check_character_parameters = all_bool_inputs (\<lambda>a. all_bool_inputs (\<lambda>b.
    char_equal (Char a False False False False False False False)
               (Char b False False False False False False False) = (a = b)))"
lemma "check_character_parameters = True" by eval

definition check_eta_parameters :: bool where
  "check_eta_parameters = all_bool_inputs (\<lambda>gate.
    all_bool_inputs (\<lambda>a. all_bool_inputs (\<lambda>b.
      eta_observe gate a b = (if gate then a else b) \<and>
      eta_case_observe gate a b = (if gate then a else b) \<and>
      eta_control_observe gate a b = (if gate then a else b))))"
lemma "check_eta_parameters = True" by eval

definition check_pending_box_fields :: bool where
  "check_pending_box_fields =
    (deep_observe \<and> frontier_observe \<and> partial_observe \<and> named_observe)"
lemma "check_pending_box_fields = True" by eval

definition check_boxed_boolean_patterns :: bool where
  "check_boxed_boolean_patterns = (cross_observe \<and>
    (case cross_rows (Node (Leaf False) (Leaf True)) of None \<Rightarrow> True | _ \<Rightarrow> False) \<and>
    (case cross_rows (Leaf True) of None \<Rightarrow> True | _ \<Rightarrow> False))"
lemma "check_boxed_boolean_patterns = True" by eval

definition check_existing_scope_controls :: bool where
  "check_existing_scope_controls = (cross_names_observe \<and>
    all_bool_inputs (\<lambda>x. all_bool_inputs (\<lambda>y.
      cap_observe x y = (x \<and> y) \<and>
      cap_named_observe x y = (if y then x else \<not> x) \<and>
      all_bool_inputs (\<lambda>a. all_bool_inputs (\<lambda>b.
        local_safe (x, y) (a, b) = ((y \<and> a) \<or> b))))))"
lemma "check_existing_scope_controls = True" by eval

(* These assertions exercise runtime semantics in both generated stages.
   make gen DIR=test/unit/terms Name=Name_Hygiene_Test
   make opt DIR=test/unit/terms Name=Name_Hygiene_Test
   Run cargo test in each stage's Name_Hygiene_Test/export1 directory. *)
code_printing code_module Name_Hygiene_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
    use crate::Name_Hygiene::*;

    #[test]
    fn direct_parameters() {
        assert!(check_direct_parameters());
    }

    #[test]
    fn character_parameters() {
        assert!(check_character_parameters());
    }

    #[test]
    fn eta_parameters() {
        assert!(check_eta_parameters());
    }

    #[test]
    fn pending_box_fields() {
        assert!(check_pending_box_fields());
    }

    #[test]
    fn boxed_boolean_patterns() {
        assert!(check_boxed_boolean_patterns());
    }

    #[test]
    fn existing_scope_controls() {
        assert!(check_existing_scope_controls());
    }
}
\<close>

export_code
  direct_same_type direct_observe frontier frontier_observe
  eta_shadow eta_observe cap_safe cap_observe
  local_safe frontier_partial partial_observe eta_control
  eta_control_observe frontier_named named_observe frontier_deep
  deep_observe cross_rows cross_observe cross_row_names
  cross_names_observe cap_named cap_named_observe
  eta_case_observe char_equal
  check_direct_parameters check_character_parameters check_eta_parameters
  check_pending_box_fields check_boxed_boolean_patterns check_existing_scope_controls
  in Rust module_name Name_Hygiene

end
