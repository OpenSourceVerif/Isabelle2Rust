theory Model imports "source/4_ds_algo/Stack_Queue/PriorityQueue_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((PriorityQueue_Test.empty :: ((nat,nat) PriorityQueue_Test.pri_queue)) ) in (List.Cons (List.length ((PriorityQueue_Test.alist_of (result)))) (List.concat (List.map (\<lambda>v. (List.append (List.Cons ((fst (v))) List.Nil) (List.Cons ((snd (v))) List.Nil))) ((PriorityQueue_Test.alist_of (result)))))))"
end
