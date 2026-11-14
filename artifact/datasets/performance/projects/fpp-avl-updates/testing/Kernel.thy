theory Kernel imports Model begin
definition kernel_prepare :: "nat list => nat tree_ht * nat list" where "kernel_prepare input = fixture input"
definition kernel_run :: "nat tree_ht * nat list => nat tree_ht" where "kernel_run n = fold step (snd n) (fst n)"
definition kernel_encode :: "nat tree_ht => nat list" where "kernel_encode result = encode_tree result"
lemma observation: "kernel_encode (kernel_run (kernel_prepare input)) = observe input"
  by (simp add: kernel_encode_def kernel_run_def kernel_prepare_def observe_def)
end
