theory Model imports Poly_Entry begin
definition decode :: "nat => int" where
  "decode w = (if even w then int (w div 2) else -int ((w+1) div 2))"
definition encode :: "int => nat" where
  "encode z = (if z < 0 then nat (-2*z-1) else nat (2*z))"
definition fixture :: "nat list => int poly * int" where
  "fixture input = (poly_of_list (map decode (tl input)), decode (hd input))"
definition observe :: "nat list => nat list" where
  "observe input = [encode (poly_entry (fst (fixture input)) (snd (fixture input)))]"
lemma fixture_representation: "fst (fixture input) = Poly (map decode (tl input))"
  by (simp add: fixture_def)
end
