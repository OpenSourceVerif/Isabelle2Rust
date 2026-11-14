theory Kernel imports Model begin
definition kernel_prepare :: "nat list => nat lheap * nat lheap" where "kernel_prepare input = Model.prepare input"
definition kernel_run :: "nat lheap * nat lheap => nat lheap" where "kernel_run p = Leftist_Heap_Test.merge (fst p) (snd p)"
definition kernel_encode :: "nat lheap => nat list" where "kernel_encode result = Model.encode_heap result"
lemma observation: "kernel_encode (kernel_run (kernel_prepare input)) = Model.observe input"
  by (simp add: kernel_encode_def kernel_run_def kernel_prepare_def Model.observe_def split: prod.splits)
end
