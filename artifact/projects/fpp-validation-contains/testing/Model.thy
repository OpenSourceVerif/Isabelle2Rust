theory Model imports Listprog_Test begin

definition chars :: "nat list \<Rightarrow> string" where
 "chars xs = map (\<lambda>n. ''abc'' ! (n mod 3)) xs"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let ys=tl input; k=hd(input@[0]) mod Suc(List.length ys) in [if Listprog_Test.contains (chars (take k ys)) (chars (drop k ys)) then 1 else 0])"
end
