theory Model imports Function_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let ys = tl input @ [0] in [Function_Test.query ys (hd (input@[0]) mod List.length ys)])"
end
