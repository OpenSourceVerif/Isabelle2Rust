theory Kernel imports Model begin
definition kernel_prepare :: "nat list \<Rightarrow> AExp_Test.aexp" where "kernel_prepare x = Model.expression x"
definition kernel_run :: "AExp_Test.aexp \<Rightarrow> Compiler_Test.instr list" where "kernel_run x = Compiler_Test.acomp x"
definition kernel_encode :: "Compiler_Test.instr list \<Rightarrow> nat list" where "kernel_encode x = concat (map Model.encode_instr x)"
lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
 by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def Model.observe_def)
end
