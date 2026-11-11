theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = concat (map (\<lambda>p. [fst p,snd p]) (Highorder_Func_Test.MapReduce input (\<lambda>x. [(x mod 3,x)]) (\<lambda>xss. map (\<lambda>k. (k, map snd (filter (\<lambda>p. fst p = k) (concat xss)))) [0,1,2]) (\<lambda>p. (fst p, sum_list (snd p)))))"

primrec wire_sum :: "nat list \<Rightarrow> nat" where
 "wire_sum [] = 0" |
 "wire_sum (x#xs) = x + wire_sum xs"
lemma wire_sum_eq_sum_list: "wire_sum xs = sum_list xs"
 by (induction xs) simp_all

declare observe_def[code del]
lemma observe_wire_code [code]:
 "observe input = concat (map (\<lambda>p. [fst p,snd p]) (Highorder_Func_Test.MapReduce input (\<lambda>x. [(x mod 3,x)]) (\<lambda>xss. map (\<lambda>k. (k, map snd (filter (\<lambda>p. fst p = k) (concat xss)))) [0,1,2]) (\<lambda>p. (fst p, wire_sum (snd p)))))"
 by (simp add: observe_def wire_sum_eq_sum_list)
end
