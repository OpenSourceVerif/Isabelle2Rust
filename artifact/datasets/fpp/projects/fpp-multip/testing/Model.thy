theory Model imports FirstExample_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [FirstExample_Test.multip (input!0) (input!1)]"
end
