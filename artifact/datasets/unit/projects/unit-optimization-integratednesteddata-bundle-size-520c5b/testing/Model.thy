theory Model imports IntegratedNestedData_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedNestedData_Test.bundle_size ((ExprBundle ((if (input ! 1) mod 4 = 0 then (EValue ((Tag ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: leaf_tag)) else (if (input ! 1) mod 4 = 1 then (ENot ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (if (input ! 1) mod 4 = 2 then (EAnd ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (EIf ((input ! 5) mod 2 = 0) ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr))))) :: bool_expr) (if (input ! 0) mod 3 = 0 then [] else [((EValue ((Tag ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: leaf_tag)) :: bool_expr), ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr)]) ((input ! 3) mod 2 = 0)) :: expr_bundle))"

end
