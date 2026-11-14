theory Model imports "source/4_ds_algo/bintree/Tree_Test" begin
primrec left_spine :: "nat list \<Rightarrow> nat Tree_Test.tree" where
 "left_spine [] = Tree_Test.Leaf" |
 "left_spine (x # xs) = Tree_Test.Node (left_spine xs) x Tree_Test.Leaf"
primrec right_spine :: "nat list \<Rightarrow> nat Tree_Test.tree" where
 "right_spine [] = Tree_Test.Leaf" |
 "right_spine (x # xs) = Tree_Test.Node Tree_Test.Leaf x (right_spine xs)"
fun balanced :: "nat \<Rightarrow> nat list \<Rightarrow> nat Tree_Test.tree" where
 "balanced 0 xs = Tree_Test.Leaf" |
 "balanced (Suc n) [] = Tree_Test.Leaf" |
 "balanced (Suc n) (x # xs) = (let k = length xs div 2 in Tree_Test.Node (balanced n (take k xs)) x (balanced n (drop k xs)))"

declare balanced.simps[code del]
lemma balanced_code[code]:
 "balanced n xs = (if n = 0 then Tree_Test.Leaf else
   (case xs of [] \<Rightarrow> Tree_Test.Leaf | x # ys \<Rightarrow>
     (let k = length ys div 2 in
      Tree_Test.Node (balanced (n - 1) (take k ys)) x (balanced (n - 1) (drop k ys)))))"
 by (cases n; cases xs) simp_all

definition fixture :: "nat list \<Rightarrow> nat Tree_Test.tree" where
 "fixture input = (case input of [] \<Rightarrow> Tree_Test.Leaf | k # xs \<Rightarrow> (if k mod 3 = 0 then left_spine xs else if k mod 3 = 1 then right_spine xs else balanced (length xs) xs))"
definition observe :: "nat list \<Rightarrow> nat list" where
 "observe input = Tree_Test.inorder (fixture input)"
end
