theory Model imports "source/2_functionalprog/Types_Test" begin
definition encode_4011ede5cd :: "((unit Types_Test.coord3d.coord3d_ext) Types_Test.coord2d.coord2d_ext) \<Rightarrow> nat list" where
 "encode_4011ede5cd i2r_record = (List.append (List.Cons (0) List.Nil) (List.append (List.Cons (if ((Types_Test.coord2d.Xpt i2r_record)) < 0 then nat (-2*((Types_Test.coord2d.Xpt i2r_record))-1) else nat (2*((Types_Test.coord2d.Xpt i2r_record)))) List.Nil) (List.append (List.Cons (if ((Types_Test.coord2d.Ypt i2r_record)) < 0 then nat (-2*((Types_Test.coord2d.Ypt i2r_record))-1) else nat (2*((Types_Test.coord2d.Ypt i2r_record)))) List.Nil) (List.append (List.append (List.Cons (0) List.Nil) (List.append (List.Cons (if ((Types_Test.coord3d.Zpt i2r_record)) < 0 then nat (-2*((Types_Test.coord3d.Zpt i2r_record))-1) else nat (2*((Types_Test.coord3d.Zpt i2r_record)))) List.Nil) (List.append (List.Cons (0) List.Nil) List.Nil))) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.coord3' :: ((unit Types_Test.coord3d.coord3d_ext) Types_Test.coord2d.coord2d_ext)) ) in (encode_4011ede5cd (result)))"
end
