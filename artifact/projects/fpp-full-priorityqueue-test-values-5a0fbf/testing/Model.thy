theory Model imports "source/4_ds_algo/Stack_Queue/PriorityQueue_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((PriorityQueue_Test.values :: (((nat,nat) PriorityQueue_Test.pri_queue) \<Rightarrow> (nat list))) ((List.fold (\<lambda>j q. PriorityQueue_Test.push j ((((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0))+j) mod 9) q) [0..<(((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) mod 4)] PriorityQueue_Test.empty))) in (List.Cons (List.length (result)) (List.concat (List.map (\<lambda>v. (List.Cons (v) List.Nil)) (result)))))"
end
