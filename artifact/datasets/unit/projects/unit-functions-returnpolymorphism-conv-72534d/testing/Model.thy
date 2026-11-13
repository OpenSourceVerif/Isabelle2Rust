theory Model imports ReturnPolymorphism_Test begin

datatype pval = PVal nat
fun unwrap_p :: "pval \<Rightarrow> nat" where "unwrap_p (PVal n) = n"
instantiation pval :: ReturnPolymorphism_Test.pseudo_num
begin
definition pn_zero_pval :: pval where "pn_zero_pval = PVal 0"
definition pn_one_pval :: pval where "pn_one_pval = PVal 1"
definition pn_add_pval :: "pval \<Rightarrow> pval \<Rightarrow> pval" where "pn_add_pval x y = PVal (unwrap_p x + unwrap_p y)"
instance ..
end


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0 in [unwrap_p (ReturnPolymorphism_Test.conv (a mod 9) :: pval)])"

end
