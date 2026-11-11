theory Model imports Set_Relation_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let vs=[''v1'',''v2'',''v3'',''v4''] in map (\<lambda>n. if (vs!(n div 4),vs!(n mod 4)) \<in> Set_Relation_Test.graph1 then 1 else 0) [0..<16])"
end
