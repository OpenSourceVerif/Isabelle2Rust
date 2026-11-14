theory Kernel imports Model begin
 definition kernel_prepare :: "nat list \<Rightarrow> string \<times> string" where
 "kernel_prepare input = (Model.chars input, Model.chars (take (hd(input@[0]) mod Suc(List.length input)) (tl input)))"
 definition kernel_run :: "string \<times> string \<Rightarrow> bool" where
 "kernel_run p = Listprog_Test.endsWith (fst p) (snd p)"
 definition kernel_encode :: "bool \<Rightarrow> nat list" where "kernel_encode b = [if b then 1 else 0]"
 lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
  by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def Model.observe_def)
 end
