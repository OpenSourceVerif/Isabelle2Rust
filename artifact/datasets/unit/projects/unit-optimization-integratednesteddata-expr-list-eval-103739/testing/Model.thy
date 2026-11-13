theory Model imports IntegratedNestedData_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "(bool list) \<Rightarrow> nat list" where
"i2r_encode_0 [] = [0]"
| "i2r_encode_0 (x # xs) = 1 # (i2r_encode_1 (x) @ i2r_encode_0 xs)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedNestedData_Test.expr_list_eval (if (input ! 0) mod 3 = 0 then [] else [((if (input ! 1) mod 4 = 0 then (EValue ((Tag ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: leaf_tag)) else (if (input ! 1) mod 4 = 1 then (ENot ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (if (input ! 1) mod 4 = 2 then (EAnd ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (EIf ((input ! 5) mod 2 = 0) ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr))))) :: bool_expr), ((if (input ! 0) mod 4 = 0 then (EValue ((Tag ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: leaf_tag)) else (if (input ! 0) mod 4 = 1 then (ENot ((EValue ((Tag ((input ! 7) mod 2 = 0) ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (if (input ! 0) mod 4 = 2 then (EAnd ((EValue ((Tag ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (EIf ((input ! 4) mod 2 = 0) ((EValue ((Tag ((input ! 7) mod 2 = 0) ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0)) :: leaf_tag)) :: bool_expr))))) :: bool_expr)]))"

end
