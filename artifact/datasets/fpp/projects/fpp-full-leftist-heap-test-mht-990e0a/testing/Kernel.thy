theory Kernel imports Model begin
definition kernel_prepare :: "nat list \<Rightarrow> nat list" where "kernel_prepare x = x"
definition kernel_run :: "nat list \<Rightarrow> nat list" where "kernel_run x = Model.observe x"
definition kernel_encode :: "nat list \<Rightarrow> nat list" where "kernel_encode x = x"
lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x" by (simp only: kernel_prepare_def kernel_run_def kernel_encode_def)
end
