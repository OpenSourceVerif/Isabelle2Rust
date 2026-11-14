theory Model imports PriorityQueue_Test begin

definition pq_pairs :: "nat list \<Rightarrow> (nat * nat) list" where
 "pq_pairs xs = zip [0..<List.length xs] (sort xs)"
definition fixture :: "nat list \<Rightarrow> (nat,nat) PriorityQueue_Test.pri_queue" where
 "fixture xs = PriorityQueue_Test.Abs_pq (pq_pairs xs)"
lemma fixture_alist [code abstract]:
 "PriorityQueue_Test.alist_of (fixture xs) = pq_pairs xs"
 unfolding fixture_def
 apply (rule PriorityQueue_Test.alist_of_Abs_pq)
 by (simp_all add: pq_pairs_def)
definition encode_pq :: "(nat,nat) PriorityQueue_Test.pri_queue \<Rightarrow> nat list" where
 "encode_pq q = concat (map (\<lambda>p. [fst p,snd p]) (PriorityQueue_Test.alist_of q))"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (case PriorityQueue_Test.pop (fixture input) of None \<Rightarrow> [0] | Some (k,q) \<Rightarrow> [1,k] @ encode_pq q)"
end
