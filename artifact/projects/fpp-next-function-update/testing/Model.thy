theory Model imports Function_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let k=hd(input@[0]); f=(\<lambda>x::nat. if x mod 2=0 then Some(Suc x) else None); g=Function_Test.update f k (List.length input) in concat(map (\<lambda>x. case g x of None \<Rightarrow> [0] | Some n \<Rightarrow> [1,n]) (input@[0,k,Suc k])))"
end
