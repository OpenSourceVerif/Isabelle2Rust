theory Entry_Left
  imports Entry_Base
begin

setup \<open>Code_Preproc.add_functrans ("afp_entry_left_rejection",
  fn _ => fn equations =>
    if exists (fn (thm, _) =>
      member (op =) (Term.add_const_names (Thm.prop_of thm) []) @{const_name probe}) equations
    then error "Tactic failed"
    else NONE)\<close>

end
