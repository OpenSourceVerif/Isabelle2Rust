theory Model imports PatternMatching_Test begin
definition I :: "int \<Rightarrow> nat list" where "I i=[nat i,nat (-i)]"
definition B :: "bool \<Rightarrow> nat list" where "B b=[if b then 1 else 0]"
definition P :: "nat * nat \<Rightarrow> nat list" where "P p=[fst p,snd p]"
definition IP :: "int * int \<Rightarrow> nat list" where "IP p=I (fst p) @ I (snd p)"
definition T3 :: "nat * nat * nat \<Rightarrow> nat list" where "T3 p=[fst p,fst (snd p),snd (snd p)]"
definition BT :: "bool * bool * bool \<Rightarrow> nat list" where "BT p=B (fst p) @ B (fst (snd p)) @ B (snd (snd p))"
fun L :: "ilist \<Rightarrow> nat list" where "L INil=[0]" | "L (ICons i t)=[1]@I i@L t"
fun F :: "(nat * nat list) option \<Rightarrow> nat list" where "F None=[0]" | "F (Some (h,t))=[1,h,length t]@t"

definition observe :: "nat list \<Rightarrow> nat list" where
 "observe input = (let x=input!0; y=input!1; z=input!2; w=input!3; a=int x-int y; b=int z-int w; flag=x mod 2=0; flag2=y mod 2=0 in
 (B (PatternMatching_Test.case_list1 (if flag then [] else [x])) @ B (PatternMatching_Test.case_list1 (if flag then [x] else [])) @ B (PatternMatching_Test.case_list1 [x,y])))"

end
