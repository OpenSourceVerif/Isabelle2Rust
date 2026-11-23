theory Residual_Binder_Scope_Test
  imports Rust_Base_Setup
begin

text \<open>
  The default equation reconstructs the original value when either nested
  pattern fails. Code-equation expansion gives sibling alternatives repeated
  binder names. A nested match must not bind one alternative's field over a
  still-live field belonging to another row's fallback.
\<close>

datatype scoped_tree =
    ScopedFlag bool
  | ScopedPair bool bool
  | ScopedMaybe "bool option"
  | ScopedBind "bool list" scoped_tree
  | ScopedApp scoped_tree scoped_tree

fun strip_scoped :: "scoped_tree \<Rightarrow> scoped_tree" where
  "strip_scoped (ScopedApp (ScopedFlag b) (ScopedBind bs t)) =
    (if b then strip_scoped t else ScopedApp (ScopedFlag b) (ScopedBind bs t))"
| "strip_scoped t = t"

fun strip_scoped_once :: "scoped_tree \<Rightarrow> scoped_tree" where
  "strip_scoped_once (ScopedApp (ScopedFlag b) (ScopedBind bs t)) =
    (if b then t else ScopedApp (ScopedFlag b) (ScopedBind bs t))"
| "strip_scoped_once t = t"

definition case_scoped :: "scoped_tree \<Rightarrow> scoped_tree" where
  "case_scoped t =
    (case t of ScopedApp (ScopedFlag b) (ScopedBind bs body) \<Rightarrow>
       (if b then body else t)
     | _ \<Rightarrow> t)"

lemma preserve_nonmatching_left:
  "strip_scoped (ScopedApp (ScopedPair a b) r) = ScopedApp (ScopedPair a b) r"
  "strip_scoped_once (ScopedApp (ScopedMaybe m) r) = ScopedApp (ScopedMaybe m) r"
  by simp_all

lemma preserve_nonmatching_right:
  "strip_scoped (ScopedApp l (ScopedFlag b)) = ScopedApp l (ScopedFlag b)"
  by (cases l) simp_all

lemma remove_matching:
  "strip_scoped_once (ScopedApp (ScopedFlag True) (ScopedBind bs t)) = t"
  by simp

export_code strip_scoped strip_scoped_once case_scoped
  in Rust module_name ResidualBinderScope

text \<open>
  Equal Rust field types can hide the same scope error from the compiler.
  Preserve the distinct Boolean payloads of nonmatching siblings at runtime.
\<close>

datatype same_scoped_tree =
    SameFlag bool
  | SameOther bool
  | SameBind bool same_scoped_tree
  | SameApp same_scoped_tree same_scoped_tree

fun strip_same_scoped :: "same_scoped_tree \<Rightarrow> same_scoped_tree" where
  "strip_same_scoped (SameApp (SameFlag b) (SameBind c t)) =
    (if b then t else SameApp (SameFlag b) (SameBind c t))"
| "strip_same_scoped t = t"

lemma distinct_siblings_preserved:
  "strip_same_scoped (SameApp (SameOther True) (SameFlag False)) =
    SameApp (SameOther True) (SameFlag False)"
  "strip_same_scoped (SameApp (SameOther False) (SameFlag True)) =
    SameApp (SameOther False) (SameFlag True)"
  by simp_all

text \<open>
  Several equations reuse the same source names, including names that can also
  be chosen for generated field and whole-value bindings. Case alternatives
  additionally retain free variables from their enclosing function.
\<close>

fun named_rows :: "same_scoped_tree \<Rightarrow> same_scoped_tree" where
  "named_rows (SameApp (SameFlag p1) (SameOther whole1)) =
    SameApp (SameOther p1) (SameFlag whole1)"
| "named_rows (SameApp (SameOther p1) (SameFlag whole1)) =
    SameApp (SameFlag whole1) (SameOther p1)"
| "named_rows (SameApp (SameBind p1 body) (SameFlag whole1)) =
    SameApp (SameBind whole1 body) (SameOther p1)"
| "named_rows t = t"

definition case_with_outer_names ::
  "bool \<Rightarrow> bool \<Rightarrow> same_scoped_tree \<Rightarrow> same_scoped_tree" where
  "case_with_outer_names p1 whole1 t =
    (case t of
       SameApp (SameFlag b) (SameOther c) \<Rightarrow>
         SameApp (SameBind p1 (SameFlag b)) (SameBind whole1 (SameOther c))
     | SameApp (SameOther b) (SameFlag c) \<Rightarrow>
         SameApp (SameBind p1 (SameOther c)) (SameBind whole1 (SameFlag b))
     | SameApp (SameBind b body) (SameFlag c) \<Rightarrow>
         SameApp (SameBind p1 (SameBind b body)) (SameBind whole1 (SameFlag c))
     | _ \<Rightarrow> SameApp (SameFlag p1) (SameApp (SameOther whole1) t))"

lemma named_rows_keep_distinct_fields:
  "named_rows (SameApp (SameOther False) (SameFlag True)) =
    SameApp (SameFlag True) (SameOther False)"
  "case_with_outer_names False True (SameApp (SameOther True) (SameFlag False)) =
    SameApp (SameBind False (SameOther False)) (SameBind True (SameFlag True))"
  by (simp_all add: case_with_outer_names_def)

export_code strip_same_scoped named_rows case_with_outer_names
  in Rust module_name SameTypeBinderScope

end
