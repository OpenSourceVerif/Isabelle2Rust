"""Source-preserving finite observation adapters for the FPP dataset."""
SIGNED=r'''
definition dec :: "nat \<Rightarrow> int" where "dec n = (if n mod 2 = 1 then - int (Suc (n div 2)) else int (n div 2))"
definition enc :: "int \<Rightarrow> nat" where "enc z = (if z < 0 then 2 * nat (-z) - 1 else 2 * nat z)"
(* Exact wire conversion avoids an incomplete generic int Ord instance in the
   existing Rust serializer. Isabelle checks this observation-only equation. *)
declare enc_def[code del]
lemma enc_integer_wire [code]:
 "enc z = (if z < 0 then 2 * nat_of_integer (integer_of_int (-z)) - 1 else 2 * nat_of_integer (integer_of_int z))"
 by (simp add: enc_def nat_of_integer.rep_eq)

'''
TREE=r'''
fun fixture :: "nat list \<Rightarrow> nat Tree_Test.tree" where
 "fixture [] = Tree_Test.Leaf" |
 "fixture [x] = Tree_Test.Node Tree_Test.Leaf x Tree_Test.Leaf" |
 "fixture (x#y#xs) = Tree_Test.Node (fixture xs) x (Tree_Test.Node Tree_Test.Leaf y Tree_Test.Leaf)"
fun encode_tree :: "nat Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l x r) = [1,x] @ encode_tree l @ encode_tree r"
'''
HTREE=r'''
primrec fixture :: "nat list \<Rightarrow> (nat * nat) Tree_Test.tree" where
 "fixture [] = Tree_Test.Leaf" |
 "fixture (x#xs) = (let t = fixture xs in Tree_Test.Node t (x, Suc (Tree_Test.height t)) Tree_Test.Leaf)"
fun encode_tree :: "(nat * nat) Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l (x,h) r) = [1,x,h] @ encode_tree l @ encode_tree r"
'''
IMP=SIGNED+r'''
primrec expression :: "nat list \<Rightarrow> AExp_Test.aexp" where
 "expression [] = AExp_Test.N 0" |
 "expression (x#xs) = AExp_Test.Plus (if x mod 3 = 0 then AExp_Test.N (dec x) else if x mod 3 = 1 then AExp_Test.V ''x'' else AExp_Test.V ''y'') (expression xs)"
definition environment :: "nat list \<Rightarrow> AExp_Test.state" where
 "environment xs = (\<lambda>v. if v = ''x'' then dec (hd (xs@[0])) else if v = ''y'' then dec (length xs) else 0)"
fun encode_exp :: "AExp_Test.aexp \<Rightarrow> nat list" where
 "encode_exp (AExp_Test.N i) = [0,enc i]" |
 "encode_exp (AExp_Test.V v) = [1,if v = ''x'' then 0 else 1]" |
 "encode_exp (AExp_Test.Plus a b) = [2] @ encode_exp a @ encode_exp b"
'''
BEXP=IMP+r'''
definition expression_b :: "nat list \<Rightarrow> BExp_Test.bexp" where
 "expression_b xs = BExp_Test.And (BExp_Test.Not (BExp_Test.Bc (length xs mod 2 = 0))) (BExp_Test.Less (expression xs) (AExp_Test.V ''x''))"
fun encode_bexp :: "BExp_Test.bexp \<Rightarrow> nat list" where
 "encode_bexp (BExp_Test.Bc b) = [0,if b then 1 else 0]" |
 "encode_bexp (BExp_Test.Not b) = [1] @ encode_bexp b" |
 "encode_bexp (BExp_Test.And a b) = [2] @ encode_bexp a @ encode_bexp b" |
 "encode_bexp (BExp_Test.Less a b) = [3] @ encode_exp a @ encode_exp b"
'''
INSTR=BEXP+r'''
fun encode_instr :: "Compiler_Test.instr \<Rightarrow> nat list" where
 "encode_instr (Compiler_Test.LOADI i) = [0,enc i]" |
 "encode_instr (Compiler_Test.LOAD v) = [1,if v = ''x'' then 0 else 1]" |
 "encode_instr Compiler_Test.ADD = [2]" |
 "encode_instr (Compiler_Test.STORE v) = [3,if v = ''x'' then 0 else 1]" |
 "encode_instr (Compiler_Test.JMP i) = [4,enc i]" |
 "encode_instr (Compiler_Test.JMPLESS i) = [5,enc i]" |
 "encode_instr (Compiler_Test.JMPGE i) = [6,enc i]"
definition instruction :: "nat list \<Rightarrow> Compiler_Test.instr" where
 "instruction xs = (case length xs mod 7 of 0 \<Rightarrow> Compiler_Test.LOADI (dec (hd (xs@[0]))) | Suc 0 \<Rightarrow> Compiler_Test.LOAD ''x'' | Suc (Suc 0) \<Rightarrow> Compiler_Test.ADD | Suc (Suc (Suc 0)) \<Rightarrow> Compiler_Test.STORE ''y'' | Suc (Suc (Suc (Suc 0))) \<Rightarrow> Compiler_Test.JMP (-2) | Suc (Suc (Suc (Suc (Suc 0)))) \<Rightarrow> Compiler_Test.JMPLESS 3 | _ \<Rightarrow> Compiler_Test.JMPGE 1)"
'''
# (case suffix, owning theory, exact export, observer, fixture declarations, input kind)
SPECS=[
 ('avl-ball','AVL_Set_Code_Test','balL','encode_tree (AVL_Set_Code_Test.balL (fixture (take (length input div 2) input)) (length input) (fixture (drop (length input div 2) input)))',HTREE,'list'),
 ('avl-balr','AVL_Set_Code_Test','balR','encode_tree (AVL_Set_Code_Test.balR (fixture (take (length input div 2) input)) (length input) (fixture (drop (length input div 2) input)))',HTREE,'list'),
 ('avl-check','AVL_Set_Test','avl','[if AVL_Set_Test.avl (fixture input) then 1 else 0]',HTREE,'list'),
 ('cmp','Cmp_Test','cmp',"[case Cmp_Test.cmp (input!0) (input!1) of Cmp_Test.LT \\<Rightarrow> 0 | Cmp_Test.EQ \\<Rightarrow> 1 | Cmp_Test.GT \\<Rightarrow> 2]",'','pair'),
 ('pred','Function_Test','Pred','(case Function_Test.Pred (input!0) of None \\<Rightarrow> [0] | Some n \\<Rightarrow> [1,n])','','unary'),
 ('mapreduce','Highorder_Func_Test','MapReduce',r'concat (map (\<lambda>p. [fst p,snd p]) (Highorder_Func_Test.MapReduce input (\<lambda>x. [(x mod 3,x)]) (\<lambda>xss. map (\<lambda>k. (k, map snd (filter (\<lambda>p. fst p = k) (concat xss)))) [0,1,2]) (\<lambda>p. (fst p, sum_list (snd p)))))','','list'),
 ('insort','InsertSort_Test','linorder_class.insort','InsertSort_Test.linorder_class.insort (length input) (sort input)','','list'),
 ('isin','Isin2_Test','isin','[if Isin2_Test.isin (fixture input) (length input mod 8) then 1 else 0]',HTREE,'list'),
 ('heap-cost','Leftist_Heap_Test','T_del_min','[Leftist_Heap_Test.T_del_min (fixture input)]',HTREE,'list'),
 ('del-list','List_Ins_Del_Test','del_list','List_Ins_Del_Test.del_list (length input mod 8) input','','list'),
 ('char-at','Listprog_Test','charAt','(if input=[] then [] else [Listprog_Test.charAt input (length input div 2)])','','list'),
 ('merge','MergeSort_Test','linorder_class.merge','MergeSort_Test.linorder_class.merge (sort (take (length input div 2) input)) (sort (drop (length input div 2) input))','','list'),
 ('prog1-add','Prog1_Test','add','[enc (Prog1_Test.add (dec (input!0)) (dec (input!1)))]',SIGNED,'pair'),
 ('prog2-add','Prog2_Test','add','[enc (Prog2_Test.add (dec (input!0)) (dec (input!1)))]',SIGNED,'pair'),
 ('deq-list','Queue_Test','deq2list','Queue_Test.deq2list input []','','list'),
 ('ack','Recursion_Test','A','[Recursion_Test.A (input!0) (input!1)]','','ack'),
 ('tree-delete','Tree_Set_Test','delete','encode_tree (Tree_Set_Test.delete (length input mod 8) (fixture input))',TREE,'list'),
 ('acomplete','Tree_Test','acomplete','[if Tree_Test.acomplete (fixture input) then 1 else 0]',TREE,'list'),
 ('tutorial-inorder','Tutorial_Test','inorder','Tutorial_Test.inorder (fixture input)',r'''primrec fixture :: "nat list \<Rightarrow> nat Tutorial_Test.tree" where
 "fixture [] = Tutorial_Test.Leaf" | "fixture (x#xs) = Tutorial_Test.Branch (fixture xs) x Tutorial_Test.Leaf"''','list'),
 ('int-insert','func_imp_compare_Test','insert','map enc (func_imp_compare_Test.insert (dec (length input)) (sort (map dec input)))',SIGNED,'list'),
 ('binary-search','search_Test','binary_search','(case search_Test.binary_search (length input mod 8) (sort input) of None \\<Rightarrow> [0] | Some n \\<Rightarrow> [1,n])','','list'),
 ('stack-empty','stack_Test','emp','[if stack_Test.emp input then 1 else 0]','','list'),
 ('add-one','Function_Test','add1','[Function_Test.add1 (input!0)]','','unary'),
 ('aval','AExp_Test','aval','[enc (AExp_Test.aval (expression input) (environment input))]',IMP,'list'),
 ('asimp-const','AExp_Test','asimp_const','encode_exp (AExp_Test.asimp_const (expression input))',IMP,'list'),
 ('asimp','AExp_Test','asimp','encode_exp (AExp_Test.asimp (expression input))',IMP,'list'),
 ('bval','BExp_Test','bval','[if BExp_Test.bval (expression_b input) (environment input) then 1 else 0]',BEXP,'list'),
 ('bsimp','BExp_Test','bsimp','encode_bexp (BExp_Test.bsimp (expression_b input))',BEXP,'list'),
 ('acomp','Compiler_Test','acomp','concat (map encode_instr (Compiler_Test.acomp (expression input)))',INSTR,'list'),
 ('bcomp','Compiler_Test','bcomp','concat (map encode_instr (Compiler_Test.bcomp (expression_b input) (length input mod 2 = 0) (-2)))',INSTR,'list'),
 ('iexec','Compiler_Test','iexec',r"""(case Compiler_Test.iexec (instruction input) (0, environment input, map dec (input@[0,1])) of (pc,s,stk) \<Rightarrow> [enc pc,enc (s ''x''),enc (s ''y''),enc (s ''z'')] @ map enc stk)""",INSTR,'list'),
 ('hof-return','Highorder_Func_Test','hof2',r'[Highorder_Func_Test.hof2 (hd (input@[0])) (\<lambda>x y. x+2*y) (length input)]','','list'),
]
KINDS={'fpp-'+row[0]:row[5] for row in SPECS}
