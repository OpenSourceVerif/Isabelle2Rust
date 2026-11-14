theory Model imports Leftist_Heap_Test begin
definition make_heap :: "nat list => nat lheap" where
  "make_heap xs = fold Leftist_Heap_Test.insert xs Leaf"
definition prepare :: "nat list => nat lheap * nat lheap" where
  "prepare input = (let n = length input div 2 in (make_heap (take n input), make_heap (drop n input)))"
fun encode_heap :: "nat lheap => nat list" where
  "encode_heap Leaf = [0]" |
  "encode_heap (Node l (x,r) t) = [1,x,r] @ encode_heap l @ encode_heap t"
definition observe :: "nat list => nat list" where
  "observe input = (case prepare input of (a,b) => encode_heap (Leftist_Heap_Test.merge a b))"
end
