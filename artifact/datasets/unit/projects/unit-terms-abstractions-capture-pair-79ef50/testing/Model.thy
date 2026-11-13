theory Model imports Abstractions_Test begin
definition I :: "int \<Rightarrow> nat list" where "I i=[nat i,nat (-i)]"
definition B :: "bool \<Rightarrow> nat list" where "B b=[if b then 1 else 0]"
definition P :: "nat * nat \<Rightarrow> nat list" where "P p=[fst p,snd p]"
definition IP :: "int * int \<Rightarrow> nat list" where "IP p=I (fst p) @ I (snd p)"
definition T3 :: "nat * nat * nat \<Rightarrow> nat list" where "T3 p=[fst p,fst (snd p),snd (snd p)]"
definition BT :: "bool * bool * bool \<Rightarrow> nat list" where "BT p=B (fst p) @ B (fst (snd p)) @ B (snd (snd p))"

definition observe :: "nat list \<Rightarrow> nat list" where
 "observe input = (let x=input!0; y=input!1; z=input!2; w=input!3; a=int x-int y; b=int z-int w; flag=x mod 2=0; flag2=y mod 2=0 in
 ((let p=Abstractions_Test.capture_pair x in [(fst p) flag,snd p])))"

end
