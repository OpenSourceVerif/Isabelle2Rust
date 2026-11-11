theory Model imports Highorder_Func_Test begin
definition chars :: "nat list \<Rightarrow> string" where
 "chars xs = map (\<lambda>n. ''abc'' ! (n mod 3)) xs"
definition encode_chars :: "string \<Rightarrow> nat list" where
 "encode_chars s = List.map (of_char :: char \<Rightarrow> nat) s"

definition pages :: "nat list \<Rightarrow> string list" where
 "pages xs = map (\<lambda>n. [[], ''a'', ''a b'', ''b a a'', ''c''] ! (n mod 5)) xs"
definition encode_counts :: "(string*nat) list \<Rightarrow> nat list" where
 "encode_counts xs = concat (map (\<lambda>p. [List.length (fst p)] @ encode_chars (fst p) @ [snd p]) xs)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_counts (Highorder_Func_Test.countwebpage (pages input) [])"
end
