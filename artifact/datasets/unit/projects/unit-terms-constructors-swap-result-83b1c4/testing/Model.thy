theory Model imports Constructors_Test begin
definition I :: "int \<Rightarrow> nat list" where "I i=[nat i,nat (-i)]"
definition B :: "bool \<Rightarrow> nat list" where "B b=[if b then 1 else 0]"
definition P :: "nat * nat \<Rightarrow> nat list" where "P p=[fst p,snd p]"
definition IP :: "int * int \<Rightarrow> nat list" where "IP p=I (fst p) @ I (snd p)"
definition T3 :: "nat * nat * nat \<Rightarrow> nat list" where "T3 p=[fst p,fst (snd p),snd (snd p)]"
definition BT :: "bool * bool * bool \<Rightarrow> nat list" where "BT p=B (fst p) @ B (fst (snd p)) @ B (snd (snd p))"
fun N :: "bitnum \<Rightarrow> nat" where "N One=1" | "N (Bit0 n)=2*N n" | "N (Bit1 n)=2*N n+1"
fun Q :: "bitnum option \<Rightarrow> nat list" where "Q None=[0]" | "Q (Some n)=[1,N n]"
fun E :: "(nat,nat) result \<Rightarrow> nat list" where "E (Ok n)=[0,n]" | "E (Err n)=[1,n]"

definition observe :: "nat list \<Rightarrow> nat list" where
 "observe input = (let x=input!0; y=input!1; z=input!2; w=input!3; a=int x-int y; b=int z-int w; flag=x mod 2=0; flag2=y mod 2=0 in
 (E (Constructors_Test.swap_result (Ok x :: (nat,nat) result)) @ E (Constructors_Test.swap_result (Err y :: (nat,nat) result))))"

end
