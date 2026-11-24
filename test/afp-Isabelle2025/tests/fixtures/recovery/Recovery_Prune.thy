theory Recovery_Prune
  imports Main "Rust.Rust_BigInt_Setup" "Go.Go_Setup"
begin

definition healthy :: "nat => nat" where "healthy n = n + 1"
definition bad_sort :: "(nat => bool) => bool" where "bad_sort P = (ALL n. P n)"
definition unknown :: "nat => nat" where "unknown n = n"

text \<open>An intentionally unclassified transformer failure exercises frozen
fallback without changing any production theory or native implementation.\<close>
setup \<open>Code_Preproc.add_functrans ("afp_recovery_unknown",
  fn _ => fn eqns =>
    if exists (fn (thm, _) =>
      member (op =) (Term.add_const_names (Thm.prop_of thm) []) @{const_name unknown}) eqns
    then raise Fail "AFP recovery fixture: unknown equation transformer"
    else NONE)\<close>

end
