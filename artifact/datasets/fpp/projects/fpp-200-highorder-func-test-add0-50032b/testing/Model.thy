theory Model imports "source/2_functionalprog/Highorder_Func_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Highorder_Func_Test.add0 :: ((int \<times> int) \<Rightarrow> int)) (((int (((input@[0,1,2,3,4,5,6,7])!0) mod 9) - 4),(int ((((input@[0,1,2,3,4,5,6,7])!0)+1) mod 9) - 4)))) in [if result < 0 then nat (-2*result-1) else nat (2*result)])"
end
