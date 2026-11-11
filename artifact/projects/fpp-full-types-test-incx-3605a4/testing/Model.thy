theory Model imports "source/2_functionalprog/Types_Test" begin
definition fixture_e4121fce0d_2 :: "nat \<Rightarrow> (unit Types_Test.coord2d.coord2d_ext)" where
 "fixture_e4121fce0d_2 s = (Types_Test.coord2d.coord2d_ext ((int ((s + 1) mod 9) - 4)) ((int ((s + 2) mod 9) - 4)) (()))"

definition encode_e4121fce0d :: "(unit Types_Test.coord2d.coord2d_ext) \<Rightarrow> nat list" where
 "encode_e4121fce0d i2r_record = (List.append (List.Cons (0) List.Nil) (List.append (List.Cons (if ((Types_Test.coord2d.Xpt i2r_record)) < 0 then nat (-2*((Types_Test.coord2d.Xpt i2r_record))-1) else nat (2*((Types_Test.coord2d.Xpt i2r_record)))) List.Nil) (List.append (List.Cons (if ((Types_Test.coord2d.Ypt i2r_record)) < 0 then nat (-2*((Types_Test.coord2d.Ypt i2r_record))-1) else nat (2*((Types_Test.coord2d.Ypt i2r_record)))) List.Nil) (List.append (List.Cons (0) List.Nil) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.incX :: ((unit Types_Test.coord2d.coord2d_ext) \<Rightarrow> (unit Types_Test.coord2d.coord2d_ext))) ((fixture_e4121fce0d_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0))))) in (encode_e4121fce0d (result)))"
end
