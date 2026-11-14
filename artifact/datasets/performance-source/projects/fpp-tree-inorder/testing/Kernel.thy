theory Kernel imports Model begin
 definition kernel_prepare :: "nat list \<Rightarrow> nat Tree_Test.tree" where "kernel_prepare x = Model.fixture x"
 definition kernel_run :: "nat Tree_Test.tree \<Rightarrow> nat list" where "kernel_run t = Tree_Test.inorder t"
 definition kernel_encode :: "nat list \<Rightarrow> nat list" where "kernel_encode x = x"
 lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
  by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def Model.observe_def)
end
