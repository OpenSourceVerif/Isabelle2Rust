module Reference : sig
  type nat
  val last_index_integer : Z.t list -> Z.t -> Z.t
end = struct

type 'a equal = {equal : 'a -> 'a -> bool};;
let equal _A = _A.equal;;

let equal_integer = ({equal = Z.equal} : Z.t equal);;

type 'a ord = {less_eq : 'a -> 'a -> bool; less : 'a -> 'a -> bool};;
let less_eq _A = _A.less_eq;;
let less _A = _A.less;;

let ord_integer = ({less_eq = Z.leq; less = Z.lt} : Z.t ord);;

type nat = Nat of Z.t;;

type num = One | Bit0 of num | Bit1 of num;;

let rec eq _A a b = equal _A a b;;

let rec integer_of_nat (Nat x) = x;;

let rec plus_nat m n = Nat (Z.add (integer_of_nat m) (integer_of_nat n));;

let one_nat : nat = Nat (Z.of_int 1);;

let rec suc n = plus_nat n one_nat;;

let rec fold f x1 s = match f, x1, s with f, x :: xs, s -> fold f xs (f x s)
               | f, [], s -> s;;

let rec rev xs = fold (fun a b -> a :: b) xs [];;

let rec gen_length n x1 = match n, x1 with n, x :: xs -> gen_length (suc n) xs
                     | n, [] -> n;;

let zero_nat : nat = Nat Z.zero;;

let rec find_index
  uu x1 = match uu, x1 with uu, [] -> zero_nat
    | p, x :: xs ->
        (if p x then zero_nat else plus_nat (find_index p xs) one_nat);;

let rec index _A xs = (fun a -> find_index (fun x -> eq _A x a) xs);;

let rec size_list x = gen_length zero_nat x;;

let rec max _A a b = (if less_eq _A a b then b else a);;

let rec minus_nat
  m n = Nat (max ord_integer Z.zero
              (Z.sub (integer_of_nat m) (integer_of_nat n)));;

let rec equal_nat m n = Z.equal (integer_of_nat m) (integer_of_nat n);;

let rec last_index _A
  xs x =
    (let i = index _A (rev xs) x in
     let n = size_list xs in
      (if equal_nat i n then i else minus_nat n (plus_nat i one_nat)));;

let rec last_index_integer
  xs x = integer_of_nat (last_index equal_integer xs x);;

end;; (*struct Reference*)
