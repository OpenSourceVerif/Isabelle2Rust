theory Model imports BasicDef_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if BasicDef_Test.AND (input!0 mod 2 = 1) (input!1 mod 2 = 1) then 1 else 0]"
end
