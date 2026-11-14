theory Model imports "source/4_ds_algo/Stack_Queue/Queue_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Queue_Test.isempty :: ((nat list) \<Rightarrow> bool)) ((map (\<lambda>j0. ((((input@[0,1,2,3,4,5,6,7])!0)+j0) mod 9)) [0..<(((input@[0,1,2,3,4,5,6,7])!0) mod 4)]))) in [if result then 1 else 0])"
end
