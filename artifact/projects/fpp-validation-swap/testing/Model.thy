theory Model imports AlgebraicStructure_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let ys=tl input@[0] in AlgebraicStructure_Test.swap ys (hd(input@[0]) mod List.length ys) (List.length ys-1))"
end
