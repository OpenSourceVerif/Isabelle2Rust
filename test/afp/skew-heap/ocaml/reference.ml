module Reference : sig
  type 'a tree = Leaf | Node of 'a tree * 'a * 'a tree
  val merge_integer : Z.t tree -> Z.t tree -> Z.t tree
end = struct

type 'a ord = {less_eq : 'a -> 'a -> bool; less : 'a -> 'a -> bool};;
let less_eq _A = _A.less_eq;;
let less _A = _A.less;;

let ord_integer = ({less_eq = Z.leq; less = Z.lt} : Z.t ord);;

type 'a preorder = {ord_preorder : 'a ord};;

type 'a order = {preorder_order : 'a preorder};;

let preorder_integer = ({ord_preorder = ord_integer} : Z.t preorder);;

let order_integer = ({preorder_order = preorder_integer} : Z.t order);;

type 'a linorder = {order_linorder : 'a order};;

let linorder_integer = ({order_linorder = order_integer} : Z.t linorder);;

type 'a tree = Leaf | Node of 'a tree * 'a * 'a tree;;

let rec merge _A
  t ta = match t, ta with Leaf, t -> t
    | t, Leaf -> t
    | Node (l1, a1, r1), Node (l2, a2, r2) ->
        (let t2 = Node (l2, a2, r2) in
         let t1 = Node (l1, a1, r1) in
          (if less_eq _A.order_linorder.preorder_order.ord_preorder a1 a2
            then Node (merge _A t2 r1, a1, l1)
            else Node (merge _A t1 r2, a2, l2)));;

let rec merge_integer a b = merge linorder_integer a b;;

end;; (*struct Reference*)
