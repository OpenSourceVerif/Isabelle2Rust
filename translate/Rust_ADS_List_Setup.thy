theory Rust_ADS_List_Setup
  imports "ADS_Functor.ADS_Construction"
begin

text \<open>
  Optional adapter for the list representation installed by ADS_Construction.
  Import it alongside the selected numeric profile and declare the ADS_Functor
  session dependency. Its lifting setup makes list_R1_to_list the executable
  constructor of HOL lists, while the underlying locale datatype has no global
  constructor registration. Register that existing datatype and express Nil and
  Cons using the selected representation; do not replace the list constructor
  set, since the lifted merge_list equations pattern-match on it.

  The inverse conversion is an executable projection by the already proved
  isomorphism. All three equations retain the original HOL values and use only
  existing constructors and ordinary function equations.
\<close>

code_datatype list_R1.list_R1

lemma rust_ads_nil_code [code]:
  "[] = list_R1.list_R1_to_list (list_R1.list_R1 (Inl ()))"
  by (simp add: list_R1.list_R1_to_list_simps)

lemma rust_ads_cons_code [code]:
  "x # list_R1.list_R1_to_list xs =
    list_R1.list_R1_to_list (list_R1.list_R1 (Inr (x, xs)))"
  by (simp add: list_R1.list_R1_to_list_simps)

declare list_R1.list_of_R1 [code]

text \<open>
  The lifted merge_list equation already uses this constructor representation.
  Its recursive worker and one-layer merge definition also live in the locale;
  expose their existing proved equations so that list clients can compute the
  merge without changing the lifted equation or its element callback.
\<close>

declare list_R1.merge_R1.simps [code]
declare list_R1.merge_F_def [code]

end
