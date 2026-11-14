theory GCD_Entry imports "HOL.GCD" "Rust.Rust_Base_Setup" begin
definition gcd_entry :: "integer => integer => integer" where
 "gcd_entry a b = gcd a b"
lemma gcd_entry_correct: "gcd_entry a b = gcd a b"
 by (simp add: gcd_entry_def)
end
