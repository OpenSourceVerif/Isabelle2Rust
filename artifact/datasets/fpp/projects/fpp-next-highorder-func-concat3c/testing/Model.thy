theory Model imports Highorder_Func_Test begin
definition chars :: "nat list \<Rightarrow> string" where
 "chars xs = map (\<lambda>n. ''abc'' ! (n mod 3)) xs"
definition encode_chars :: "string \<Rightarrow> nat list" where
 "encode_chars s = List.map (of_char :: char \<Rightarrow> nat) s"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let n=List.length input div 3 in encode_chars (Highorder_Func_Test.concat3c (chars (take n input)) (chars (take n (drop n input)),chars (drop (2*n) input))))"
end
