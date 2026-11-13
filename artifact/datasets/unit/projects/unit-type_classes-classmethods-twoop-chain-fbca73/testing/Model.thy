theory Model imports ClassMethods_Test begin
instantiation nat :: inc
begin
definition inc_nat where "inc (x::nat) = x + 1"
instance ..
end
instantiation nat :: combine
begin
definition combine_nat where "combine (x::nat) y = x + y"
instance ..
end
instantiation nat :: chooser
begin
definition pick_method_nat where "pick_method b (x::nat) y = (if b then x else y)"
instance ..
end
instantiation nat :: twoop
begin
definition op1_nat where "op1 (x::nat) y = x + y"
definition op2_nat where "op2 (x::nat) y = x * y"
instance ..
end
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ClassMethods_Test.twoop_chain (input ! 0) (input ! 1) (input ! 2))"

end
