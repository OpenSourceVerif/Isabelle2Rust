theory Kernel imports Model begin
 definition kernel_prepare :: "nat list \<Rightarrow> nat \<times> nat" where "kernel_prepare x = (x!0, x!1)"
 definition kernel_run :: "nat \<times> nat \<Rightarrow> nat" where "kernel_run p = FirstExample_Test.multip (fst p) (snd p)"
 definition kernel_encode :: "nat \<Rightarrow> nat list" where "kernel_encode x = [x]"
 lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
  by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def Model.observe_def)
 end
