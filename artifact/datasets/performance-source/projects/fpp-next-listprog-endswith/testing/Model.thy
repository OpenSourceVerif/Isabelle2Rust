theory Model imports Listprog_Test begin
definition chars :: "nat list \<Rightarrow> string" where
 "chars xs = map (\<lambda>n. ''abc'' ! (n mod 3)) xs"
definition encode_chars :: "string \<Rightarrow> nat list" where
 "encode_chars s = List.map (of_char :: char \<Rightarrow> nat) s"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if Listprog_Test.endsWith (chars input) (chars (take (hd(input@[0]) mod Suc(List.length input)) (tl input))) then 1 else 0]"
end
