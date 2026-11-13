theory Model imports HigherOrder_Test begin

definition decode_int :: "nat \<Rightarrow> int" where
  "decode_int n = (if n mod 2 = 0 then int (n div 2) else - int (n div 2) - 1)"
definition encode_int :: "int \<Rightarrow> nat" where
  "encode_int z = (if 0 \<le> z then 2 * nat z else 2 * nat (-z) - 1)"

datatype hval = HVal nat
fun unwrap_h :: "hval \<Rightarrow> nat" where "unwrap_h (HVal n) = n"
instantiation hval :: HigherOrder_Test.my_cls
begin
definition my_op_hval :: "hval \<Rightarrow> hval" where "my_op_hval x = HVal (unwrap_h x + 2)"
instance ..
end


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; i = decode_int a; j = decode_int b; k = decode_int c in [HigherOrder_Test.apply_twice (\<lambda>x. x + 1) a])"

end
