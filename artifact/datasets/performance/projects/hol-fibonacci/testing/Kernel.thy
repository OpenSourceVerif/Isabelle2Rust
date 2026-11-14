theory Kernel imports Model begin
definition kernel_prepare :: "nat list => nat" where "kernel_prepare input = hd input"
definition kernel_run :: "nat => nat" where "kernel_run n = Fib.fib n"
definition kernel_encode :: "nat => nat list" where "kernel_encode result = [result]"
lemma observation: "kernel_encode (kernel_run (kernel_prepare input)) = observe input"
  by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def observe_def)
end
