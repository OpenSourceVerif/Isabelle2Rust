theory Model imports "source/2_functionalprog/Types_Test" begin
definition encode_916aadeef1 :: "((int,unit) Types_Test.Coord3d.Coord3d_ext) \<Rightarrow> nat list" where
 "encode_916aadeef1 i2r_record = (List.append (List.Cons (0) List.Nil) (List.append (List.Cons (if ((Types_Test.Coord3d.xpos i2r_record)) < 0 then nat (-2*((Types_Test.Coord3d.xpos i2r_record))-1) else nat (2*((Types_Test.Coord3d.xpos i2r_record)))) List.Nil) (List.append (List.Cons (if ((Types_Test.Coord3d.ypos i2r_record)) < 0 then nat (-2*((Types_Test.Coord3d.ypos i2r_record))-1) else nat (2*((Types_Test.Coord3d.ypos i2r_record)))) List.Nil) (List.append (List.Cons (if ((Types_Test.Coord3d.zpos i2r_record)) < 0 then nat (-2*((Types_Test.Coord3d.zpos i2r_record))-1) else nat (2*((Types_Test.Coord3d.zpos i2r_record)))) List.Nil) (List.append (List.Cons (0) List.Nil) List.Nil)))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.coord6 :: ((int,unit) Types_Test.Coord3d.Coord3d_ext)) ) in (encode_916aadeef1 (result)))"
end
