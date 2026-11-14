theory Kernel imports Model begin
definition kernel_prepare :: "nat list => integer * integer" where
 "kernel_prepare input = (decode (input!0), decode (input!1))"
definition kernel_run :: "integer * integer => integer" where
 "kernel_run p = GCD_Entry.gcd_entry (fst p) (snd p)"
definition kernel_encode :: "integer => nat list" where
 "kernel_encode r = [nat_of_integer r]"
lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
 by (simp add: kernel_encode_def kernel_run_def kernel_prepare_def Model.observe_def)
end
