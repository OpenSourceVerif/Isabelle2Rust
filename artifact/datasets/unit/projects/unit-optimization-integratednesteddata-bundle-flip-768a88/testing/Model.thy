theory Model imports IntegratedNestedData_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "leaf_tag \<Rightarrow> nat list" where
"i2r_encode_2 (Tag x0 x1 x2) = [0] @ i2r_encode_3 (x0) @ i2r_encode_3 (x1) @ i2r_encode_3 (x2)"

fun i2r_encode_1 :: "bool_expr \<Rightarrow> nat list" where
"i2r_encode_1 (EValue x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (ENot x0) = [1] @ i2r_encode_1 (x0)"
| "i2r_encode_1 (EAnd x0 x1) = [2] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"
| "i2r_encode_1 (EIf x0 x1 x2) = [3] @ i2r_encode_3 (x0) @ i2r_encode_1 (x1) @ i2r_encode_1 (x2)"

fun i2r_encode_4 :: "(bool_expr list) \<Rightarrow> nat list" where
"i2r_encode_4 [] = [0]"
| "i2r_encode_4 (x # xs) = 1 # (i2r_encode_1 (x) @ i2r_encode_4 xs)"

fun i2r_encode_0 :: "expr_bundle \<Rightarrow> nat list" where
"i2r_encode_0 (ExprBundle x0 x1 x2) = [0] @ i2r_encode_1 (x0) @ i2r_encode_4 (x1) @ i2r_encode_3 (x2)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedNestedData_Test.bundle_flip ((ExprBundle ((if (input ! 1) mod 4 = 0 then (EValue ((Tag ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: leaf_tag)) else (if (input ! 1) mod 4 = 1 then (ENot ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (if (input ! 1) mod 4 = 2 then (EAnd ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: leaf_tag)) :: bool_expr)) else (EIf ((input ! 5) mod 2 = 0) ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr) ((EValue ((Tag ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: leaf_tag)) :: bool_expr))))) :: bool_expr) (if (input ! 0) mod 3 = 0 then [] else [((EValue ((Tag ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: leaf_tag)) :: bool_expr), ((EValue ((Tag ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: leaf_tag)) :: bool_expr)]) ((input ! 3) mod 2 = 0)) :: expr_bundle))"

end
