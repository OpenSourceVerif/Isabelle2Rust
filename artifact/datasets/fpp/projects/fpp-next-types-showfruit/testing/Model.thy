theory Model imports Types_Test begin
definition chars :: "nat list \<Rightarrow> string" where
 "chars xs = map (\<lambda>n. ''abc'' ! (n mod 3)) xs"
definition encode_chars :: "string \<Rightarrow> nat list" where
 "encode_chars s = List.map (of_char :: char \<Rightarrow> nat) s"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_chars (Types_Test.showfruit (if hd(input@[0]) mod 3=0 then Types_Test.APPLE else if hd(input@[0]) mod 3=1 then Types_Test.ORANGE else Types_Test.BANANA))"
end
