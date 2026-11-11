theory Model imports "source/2_functionalprog/Function_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Function_Test.fun1 :: (int \<Rightarrow> int)) ((int (((input@[0,1,2,3,4,5,6,7])!0) mod 9) - 4))) in [if result < 0 then nat (-2*result-1) else nat (2*result)])"
end
