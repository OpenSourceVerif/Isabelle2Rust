module X64_step_test : sig
  type myint
  type 'a word
  type preg
  type 'a bit0
  type num1
  type vala
  type outcome
  type bit_mode
  val int64_to_myint : int64 -> myint
  val int64_list_to_myint_list : int64 list -> myint list
  val x64_step_test :
    myint -> myint list -> myint list -> myint list -> myint list -> int64 list
end = struct

type num = One | Bit0 of num | Bit1 of num;;

let rec plus_num
  x0 x1 = match x0, x1 with Bit1 m, Bit1 n -> Bit0 (plus_num (plus_num m n) One)
    | Bit1 m, Bit0 n -> Bit1 (plus_num m n)
    | Bit1 m, One -> Bit0 (plus_num m One)
    | Bit0 m, Bit1 n -> Bit1 (plus_num m n)
    | Bit0 m, Bit0 n -> Bit0 (plus_num m n)
    | Bit0 m, One -> Bit1 m
    | One, Bit1 n -> Bit0 (plus_num n One)
    | One, Bit0 n -> Bit1 n
    | One, One -> Bit0 One;;

let rec times_num
  m n = match m, n with
    Bit1 m, Bit1 n -> Bit1 (plus_num (plus_num m n) (Bit0 (times_num m n)))
    | Bit1 m, Bit0 n -> Bit0 (times_num (Bit1 m) n)
    | Bit0 m, Bit1 n -> Bit0 (times_num m (Bit1 n))
    | Bit0 m, Bit0 n -> Bit0 (Bit0 (times_num m n))
    | One, n -> n
    | m, One -> m;;

type myint = Zero_int | Pos of num | Neg of num;;

let rec times_inta k l = match k, l with Neg m, Neg n -> Pos (times_num m n)
                     | Neg m, Pos n -> Neg (times_num m n)
                     | Pos m, Neg n -> Neg (times_num m n)
                     | Pos m, Pos n -> Pos (times_num m n)
                     | Zero_int, l -> Zero_int
                     | k, Zero_int -> Zero_int;;

type 'a times = {times : 'a -> 'a -> 'a};;
let times _A = _A.times;;

type 'a dvd = {times_dvd : 'a times};;

let times_int = ({times = times_inta} : myint times);;

let dvd_int = ({times_dvd = times_int} : myint dvd);;

let one_inta : myint = Pos One;;

type 'a one = {one : 'a};;
let one _A = _A.one;;

let one_int = ({one = one_inta} : myint one);;

let rec uminus_inta = function Neg m -> Pos m
                      | Pos m -> Neg m
                      | Zero_int -> Zero_int;;

let rec bitM = function One -> One
               | Bit0 n -> Bit1 (bitM n)
               | Bit1 n -> Bit1 (Bit0 n);;

let rec dup = function Neg n -> Neg (Bit0 n)
              | Pos n -> Pos (Bit0 n)
              | Zero_int -> Zero_int;;

let rec minus_inta k l = match k, l with Neg m, Neg n -> sub n m
                     | Neg m, Pos n -> Neg (plus_num m n)
                     | Pos m, Neg n -> Pos (plus_num m n)
                     | Pos m, Pos n -> sub m n
                     | Zero_int, l -> uminus_inta l
                     | k, Zero_int -> k
and sub
  x0 x1 = match x0, x1 with
    Bit0 m, Bit1 n -> minus_inta (dup (sub m n)) one_inta
    | Bit1 m, Bit0 n -> plus_inta (dup (sub m n)) one_inta
    | Bit1 m, Bit1 n -> dup (sub m n)
    | Bit0 m, Bit0 n -> dup (sub m n)
    | One, Bit1 n -> Neg (Bit0 n)
    | One, Bit0 n -> Neg (bitM n)
    | Bit1 m, One -> Pos (Bit0 m)
    | Bit0 m, One -> Pos (bitM m)
    | One, One -> Zero_int
and plus_inta k l = match k, l with Neg m, Neg n -> Neg (plus_num m n)
                | Neg m, Pos n -> sub n m
                | Pos m, Neg n -> sub m n
                | Pos m, Pos n -> Pos (plus_num m n)
                | Zero_int, l -> l
                | k, Zero_int -> k;;

type 'a uminus = {uminus : 'a -> 'a};;
let uminus _A = _A.uminus;;

type 'a minus = {minus : 'a -> 'a -> 'a};;
let minus _A = _A.minus;;

type 'a zero = {zero : 'a};;
let zero _A = _A.zero;;

type 'a plus = {plus : 'a -> 'a -> 'a};;
let plus _A = _A.plus;;

type 'a semigroup_add = {plus_semigroup_add : 'a plus};;

type 'a cancel_semigroup_add =
  {semigroup_add_cancel_semigroup_add : 'a semigroup_add};;

type 'a ab_semigroup_add = {semigroup_add_ab_semigroup_add : 'a semigroup_add};;

type 'a cancel_ab_semigroup_add =
  {ab_semigroup_add_cancel_ab_semigroup_add : 'a ab_semigroup_add;
    cancel_semigroup_add_cancel_ab_semigroup_add : 'a cancel_semigroup_add;
    minus_cancel_ab_semigroup_add : 'a minus};;

type 'a monoid_add =
  {semigroup_add_monoid_add : 'a semigroup_add; zero_monoid_add : 'a zero};;

type 'a comm_monoid_add =
  {ab_semigroup_add_comm_monoid_add : 'a ab_semigroup_add;
    monoid_add_comm_monoid_add : 'a monoid_add};;

type 'a cancel_comm_monoid_add =
  {cancel_ab_semigroup_add_cancel_comm_monoid_add : 'a cancel_ab_semigroup_add;
    comm_monoid_add_cancel_comm_monoid_add : 'a comm_monoid_add};;

type 'a mult_zero = {times_mult_zero : 'a times; zero_mult_zero : 'a zero};;

type 'a semigroup_mult = {times_semigroup_mult : 'a times};;

type 'a semiring =
  {ab_semigroup_add_semiring : 'a ab_semigroup_add;
    semigroup_mult_semiring : 'a semigroup_mult};;

type 'a semiring_0 =
  {comm_monoid_add_semiring_0 : 'a comm_monoid_add;
    mult_zero_semiring_0 : 'a mult_zero; semiring_semiring_0 : 'a semiring};;

type 'a semiring_0_cancel =
  {cancel_comm_monoid_add_semiring_0_cancel : 'a cancel_comm_monoid_add;
    semiring_0_semiring_0_cancel : 'a semiring_0};;

type 'a group_add =
  {cancel_semigroup_add_group_add : 'a cancel_semigroup_add;
    minus_group_add : 'a minus; monoid_add_group_add : 'a monoid_add;
    uminus_group_add : 'a uminus};;

type 'a ab_group_add =
  {cancel_comm_monoid_add_ab_group_add : 'a cancel_comm_monoid_add;
    group_add_ab_group_add : 'a group_add};;

type 'a ring =
  {ab_group_add_ring : 'a ab_group_add;
    semiring_0_cancel_ring : 'a semiring_0_cancel};;

let plus_int = ({plus = plus_inta} : myint plus);;

let semigroup_add_int = ({plus_semigroup_add = plus_int} : myint semigroup_add);;

let cancel_semigroup_add_int =
  ({semigroup_add_cancel_semigroup_add = semigroup_add_int} :
    myint cancel_semigroup_add);;

let ab_semigroup_add_int =
  ({semigroup_add_ab_semigroup_add = semigroup_add_int} :
    myint ab_semigroup_add);;

let minus_int = ({minus = minus_inta} : myint minus);;

let cancel_ab_semigroup_add_int =
  ({ab_semigroup_add_cancel_ab_semigroup_add = ab_semigroup_add_int;
     cancel_semigroup_add_cancel_ab_semigroup_add = cancel_semigroup_add_int;
     minus_cancel_ab_semigroup_add = minus_int}
    : myint cancel_ab_semigroup_add);;

let zero_int = ({zero = Zero_int} : myint zero);;

let monoid_add_int =
  ({semigroup_add_monoid_add = semigroup_add_int; zero_monoid_add = zero_int} :
    myint monoid_add);;

let comm_monoid_add_int =
  ({ab_semigroup_add_comm_monoid_add = ab_semigroup_add_int;
     monoid_add_comm_monoid_add = monoid_add_int}
    : myint comm_monoid_add);;

let cancel_comm_monoid_add_int =
  ({cancel_ab_semigroup_add_cancel_comm_monoid_add =
      cancel_ab_semigroup_add_int;
     comm_monoid_add_cancel_comm_monoid_add = comm_monoid_add_int}
    : myint cancel_comm_monoid_add);;

let mult_zero_int =
  ({times_mult_zero = times_int; zero_mult_zero = zero_int} : myint mult_zero);;

let semigroup_mult_int =
  ({times_semigroup_mult = times_int} : myint semigroup_mult);;

let semiring_int =
  ({ab_semigroup_add_semiring = ab_semigroup_add_int;
     semigroup_mult_semiring = semigroup_mult_int}
    : myint semiring);;

let semiring_0_int =
  ({comm_monoid_add_semiring_0 = comm_monoid_add_int;
     mult_zero_semiring_0 = mult_zero_int; semiring_semiring_0 = semiring_int}
    : myint semiring_0);;

let semiring_0_cancel_int =
  ({cancel_comm_monoid_add_semiring_0_cancel = cancel_comm_monoid_add_int;
     semiring_0_semiring_0_cancel = semiring_0_int}
    : myint semiring_0_cancel);;

let uminus_int = ({uminus = uminus_inta} : myint uminus);;

let group_add_int =
  ({cancel_semigroup_add_group_add = cancel_semigroup_add_int;
     minus_group_add = minus_int; monoid_add_group_add = monoid_add_int;
     uminus_group_add = uminus_int}
    : myint group_add);;

let ab_group_add_int =
  ({cancel_comm_monoid_add_ab_group_add = cancel_comm_monoid_add_int;
     group_add_ab_group_add = group_add_int}
    : myint ab_group_add);;

let ring_int =
  ({ab_group_add_ring = ab_group_add_int;
     semiring_0_cancel_ring = semiring_0_cancel_int}
    : myint ring);;

type 'a numeral =
  {one_numeral : 'a one; semigroup_add_numeral : 'a semigroup_add};;

let numeral_int =
  ({one_numeral = one_int; semigroup_add_numeral = semigroup_add_int} :
    myint numeral);;

type 'a power = {one_power : 'a one; times_power : 'a times};;

let power_int = ({one_power = one_int; times_power = times_int} : myint power);;

let rec less_eq_num x0 n = match x0, n with Bit1 m, Bit0 n -> less_num m n
                      | Bit1 m, Bit1 n -> less_eq_num m n
                      | Bit0 m, Bit1 n -> less_eq_num m n
                      | Bit0 m, Bit0 n -> less_eq_num m n
                      | Bit1 m, One -> false
                      | Bit0 m, One -> false
                      | One, n -> true
and less_num m x1 = match m, x1 with Bit1 m, Bit0 n -> less_num m n
               | Bit1 m, Bit1 n -> less_num m n
               | Bit0 m, Bit1 n -> less_eq_num m n
               | Bit0 m, Bit0 n -> less_num m n
               | One, Bit1 n -> true
               | One, Bit0 n -> true
               | m, One -> false;;

let rec less_eq_int x0 x1 = match x0, x1 with Neg k, Neg l -> less_eq_num l k
                      | Neg k, Pos l -> true
                      | Neg k, Zero_int -> true
                      | Pos k, Neg l -> false
                      | Pos k, Pos l -> less_eq_num k l
                      | Pos k, Zero_int -> false
                      | Zero_int, Neg l -> false
                      | Zero_int, Pos l -> true
                      | Zero_int, Zero_int -> true;;

let rec less_int x0 x1 = match x0, x1 with Neg k, Neg l -> less_num l k
                   | Neg k, Pos l -> true
                   | Neg k, Zero_int -> true
                   | Pos k, Neg l -> false
                   | Pos k, Pos l -> less_num k l
                   | Pos k, Zero_int -> false
                   | Zero_int, Neg l -> false
                   | Zero_int, Pos l -> true
                   | Zero_int, Zero_int -> false;;

let rec abs_int i = (if less_int i Zero_int then uminus_inta i else i);;

let rec divmod_step_int
  l qr =
    (let (q, r) = qr in
      (if less_eq_int (abs_int l) (abs_int r)
        then (plus_inta (times_inta (Pos (Bit0 One)) q) one_inta,
               minus_inta r l)
        else (times_inta (Pos (Bit0 One)) q, r)));;

let rec divmod_int
  m x1 = match m, x1 with
    Bit1 m, Bit1 n ->
      (if less_num m n then (Zero_int, Pos (Bit1 m))
        else divmod_step_int (Pos (Bit1 n))
               (divmod_int (Bit1 m) (Bit0 (Bit1 n))))
    | Bit0 m, Bit1 n ->
        (if less_eq_num m n then (Zero_int, Pos (Bit0 m))
          else divmod_step_int (Pos (Bit1 n))
                 (divmod_int (Bit0 m) (Bit0 (Bit1 n))))
    | Bit1 m, Bit0 n ->
        (let (q, r) = divmod_int m n in
          (q, plus_inta (times_inta (Pos (Bit0 One)) r) one_inta))
    | Bit0 m, Bit0 n ->
        (let (q, r) = divmod_int m n in (q, times_inta (Pos (Bit0 One)) r))
    | One, Bit1 n -> (Zero_int, Pos One)
    | One, Bit0 n -> (Zero_int, Pos One)
    | m, One -> (Pos m, Zero_int);;

let rec fst (x1, x2) = x1;;

type 'a zero_neq_one =
  {one_zero_neq_one : 'a one; zero_zero_neq_one : 'a zero};;

let rec of_bool _A = function true -> one _A.one_zero_neq_one
                     | false -> zero _A.zero_zero_neq_one;;

let rec equal_num x0 x1 = match x0, x1 with Bit0 x2, Bit1 x3 -> false
                    | Bit1 x3, Bit0 x2 -> false
                    | One, Bit1 x3 -> false
                    | Bit1 x3, One -> false
                    | One, Bit0 x2 -> false
                    | Bit0 x2, One -> false
                    | Bit1 x3, Bit1 y3 -> equal_num x3 y3
                    | Bit0 x2, Bit0 y2 -> equal_num x2 y2
                    | One, One -> true;;

let rec equal_int x0 x1 = match x0, x1 with Neg k, Neg l -> equal_num k l
                    | Neg k, Pos l -> false
                    | Neg k, Zero_int -> false
                    | Pos k, Neg l -> false
                    | Pos k, Pos l -> equal_num k l
                    | Pos k, Zero_int -> false
                    | Zero_int, Neg l -> false
                    | Zero_int, Pos l -> false
                    | Zero_int, Zero_int -> true;;

let zero_neq_one_int =
  ({one_zero_neq_one = one_int; zero_zero_neq_one = zero_int} :
    myint zero_neq_one);;

let rec adjust_div
  (q, r) = plus_inta q (of_bool zero_neq_one_int (not (equal_int r Zero_int)));;

let rec divide_inta
  k ka = match k, ka with Neg m, Neg n -> fst (divmod_int m n)
    | Pos m, Neg n -> uminus_inta (adjust_div (divmod_int m n))
    | Neg m, Pos n -> uminus_inta (adjust_div (divmod_int m n))
    | Pos m, Pos n -> fst (divmod_int m n)
    | k, Neg One -> uminus_inta k
    | k, Pos One -> k
    | Zero_int, k -> Zero_int
    | k, Zero_int -> Zero_int;;

type 'a divide = {divide : 'a -> 'a -> 'a};;
let divide _A = _A.divide;;

let divide_int = ({divide = divide_inta} : myint divide);;

let rec snd (x1, x2) = x2;;

let rec adjust_mod
  l r = (if equal_int r Zero_int then Zero_int else minus_inta (Pos l) r);;

let rec modulo_inta
  k ka = match k, ka with Neg m, Neg n -> uminus_inta (snd (divmod_int m n))
    | Pos m, Neg n -> uminus_inta (adjust_mod n (snd (divmod_int m n)))
    | Neg m, Pos n -> adjust_mod n (snd (divmod_int m n))
    | Pos m, Pos n -> snd (divmod_int m n)
    | k, Neg One -> Zero_int
    | k, Pos One -> Zero_int
    | Zero_int, k -> Zero_int
    | k, Zero_int -> k;;

type 'a modulo =
  {divide_modulo : 'a divide; dvd_modulo : 'a dvd; modulo : 'a -> 'a -> 'a};;
let modulo _A = _A.modulo;;

let modulo_int =
  ({divide_modulo = divide_int; dvd_modulo = dvd_int; modulo = modulo_inta} :
    myint modulo);;

type 'a monoid_mult =
  {semigroup_mult_monoid_mult : 'a semigroup_mult;
    power_monoid_mult : 'a power};;

type 'a semiring_numeral =
  {monoid_mult_semiring_numeral : 'a monoid_mult;
    numeral_semiring_numeral : 'a numeral;
    semiring_semiring_numeral : 'a semiring};;

type 'a semiring_1 =
  {semiring_numeral_semiring_1 : 'a semiring_numeral;
    semiring_0_semiring_1 : 'a semiring_0;
    zero_neq_one_semiring_1 : 'a zero_neq_one};;

type 'a semiring_1_cancel =
  {semiring_0_cancel_semiring_1_cancel : 'a semiring_0_cancel;
    semiring_1_semiring_1_cancel : 'a semiring_1};;

type 'a neg_numeral =
  {group_add_neg_numeral : 'a group_add; numeral_neg_numeral : 'a numeral};;

type 'a ring_1 =
  {neg_numeral_ring_1 : 'a neg_numeral; ring_ring_1 : 'a ring;
    semiring_1_cancel_ring_1 : 'a semiring_1_cancel};;

let monoid_mult_int =
  ({semigroup_mult_monoid_mult = semigroup_mult_int;
     power_monoid_mult = power_int}
    : myint monoid_mult);;

let semiring_numeral_int =
  ({monoid_mult_semiring_numeral = monoid_mult_int;
     numeral_semiring_numeral = numeral_int;
     semiring_semiring_numeral = semiring_int}
    : myint semiring_numeral);;

let semiring_1_int =
  ({semiring_numeral_semiring_1 = semiring_numeral_int;
     semiring_0_semiring_1 = semiring_0_int;
     zero_neq_one_semiring_1 = zero_neq_one_int}
    : myint semiring_1);;

let semiring_1_cancel_int =
  ({semiring_0_cancel_semiring_1_cancel = semiring_0_cancel_int;
     semiring_1_semiring_1_cancel = semiring_1_int}
    : myint semiring_1_cancel);;

let neg_numeral_int =
  ({group_add_neg_numeral = group_add_int; numeral_neg_numeral = numeral_int} :
    myint neg_numeral);;

let ring_1_int =
  ({neg_numeral_ring_1 = neg_numeral_int; ring_ring_1 = ring_int;
     semiring_1_cancel_ring_1 = semiring_1_cancel_int}
    : myint ring_1);;

type 'a ab_semigroup_mult =
  {semigroup_mult_ab_semigroup_mult : 'a semigroup_mult};;

type 'a comm_semiring =
  {ab_semigroup_mult_comm_semiring : 'a ab_semigroup_mult;
    semiring_comm_semiring : 'a semiring};;

type 'a comm_semiring_0 =
  {comm_semiring_comm_semiring_0 : 'a comm_semiring;
    semiring_0_comm_semiring_0 : 'a semiring_0};;

type 'a comm_semiring_0_cancel =
  {comm_semiring_0_comm_semiring_0_cancel : 'a comm_semiring_0;
    semiring_0_cancel_comm_semiring_0_cancel : 'a semiring_0_cancel};;

type 'a comm_ring =
  {comm_semiring_0_cancel_comm_ring : 'a comm_semiring_0_cancel;
    ring_comm_ring : 'a ring};;

let ab_semigroup_mult_int =
  ({semigroup_mult_ab_semigroup_mult = semigroup_mult_int} :
    myint ab_semigroup_mult);;

let comm_semiring_int =
  ({ab_semigroup_mult_comm_semiring = ab_semigroup_mult_int;
     semiring_comm_semiring = semiring_int}
    : myint comm_semiring);;

let comm_semiring_0_int =
  ({comm_semiring_comm_semiring_0 = comm_semiring_int;
     semiring_0_comm_semiring_0 = semiring_0_int}
    : myint comm_semiring_0);;

let comm_semiring_0_cancel_int =
  ({comm_semiring_0_comm_semiring_0_cancel = comm_semiring_0_int;
     semiring_0_cancel_comm_semiring_0_cancel = semiring_0_cancel_int}
    : myint comm_semiring_0_cancel);;

let comm_ring_int =
  ({comm_semiring_0_cancel_comm_ring = comm_semiring_0_cancel_int;
     ring_comm_ring = ring_int}
    : myint comm_ring);;

type 'a comm_monoid_mult =
  {ab_semigroup_mult_comm_monoid_mult : 'a ab_semigroup_mult;
    monoid_mult_comm_monoid_mult : 'a monoid_mult;
    dvd_comm_monoid_mult : 'a dvd};;

type 'a comm_semiring_1 =
  {comm_monoid_mult_comm_semiring_1 : 'a comm_monoid_mult;
    comm_semiring_0_comm_semiring_1 : 'a comm_semiring_0;
    semiring_1_comm_semiring_1 : 'a semiring_1};;

type 'a comm_semiring_1_cancel =
  {comm_semiring_0_cancel_comm_semiring_1_cancel : 'a comm_semiring_0_cancel;
    comm_semiring_1_comm_semiring_1_cancel : 'a comm_semiring_1;
    semiring_1_cancel_comm_semiring_1_cancel : 'a semiring_1_cancel};;

type 'a comm_ring_1 =
  {comm_ring_comm_ring_1 : 'a comm_ring;
    comm_semiring_1_cancel_comm_ring_1 : 'a comm_semiring_1_cancel;
    ring_1_comm_ring_1 : 'a ring_1};;

let comm_monoid_mult_int =
  ({ab_semigroup_mult_comm_monoid_mult = ab_semigroup_mult_int;
     monoid_mult_comm_monoid_mult = monoid_mult_int;
     dvd_comm_monoid_mult = dvd_int}
    : myint comm_monoid_mult);;

let comm_semiring_1_int =
  ({comm_monoid_mult_comm_semiring_1 = comm_monoid_mult_int;
     comm_semiring_0_comm_semiring_1 = comm_semiring_0_int;
     semiring_1_comm_semiring_1 = semiring_1_int}
    : myint comm_semiring_1);;

let comm_semiring_1_cancel_int =
  ({comm_semiring_0_cancel_comm_semiring_1_cancel = comm_semiring_0_cancel_int;
     comm_semiring_1_comm_semiring_1_cancel = comm_semiring_1_int;
     semiring_1_cancel_comm_semiring_1_cancel = semiring_1_cancel_int}
    : myint comm_semiring_1_cancel);;

let comm_ring_1_int =
  ({comm_ring_comm_ring_1 = comm_ring_int;
     comm_semiring_1_cancel_comm_ring_1 = comm_semiring_1_cancel_int;
     ring_1_comm_ring_1 = ring_1_int}
    : myint comm_ring_1);;

type 'a semiring_modulo =
  {comm_semiring_1_cancel_semiring_modulo : 'a comm_semiring_1_cancel;
    modulo_semiring_modulo : 'a modulo};;

type 'a semiring_parity =
  {semiring_modulo_semiring_parity : 'a semiring_modulo};;

type 'a ring_parity =
  {semiring_parity_ring_parity : 'a semiring_parity;
    comm_ring_1_ring_parity : 'a comm_ring_1};;

let semiring_modulo_int =
  ({comm_semiring_1_cancel_semiring_modulo = comm_semiring_1_cancel_int;
     modulo_semiring_modulo = modulo_int}
    : myint semiring_modulo);;

let semiring_parity_int =
  ({semiring_modulo_semiring_parity = semiring_modulo_int} :
    myint semiring_parity);;

let ring_parity_int =
  ({semiring_parity_ring_parity = semiring_parity_int;
     comm_ring_1_ring_parity = comm_ring_1_int}
    : myint ring_parity);;

type 'a divide_trivial =
  {one_divide_trivial : 'a one; zero_divide_trivial : 'a zero;
    divide_divide_trivial : 'a divide};;

let divide_trivial_int =
  ({one_divide_trivial = one_int; zero_divide_trivial = zero_int;
     divide_divide_trivial = divide_int}
    : myint divide_trivial);;

type nat = Zero_nat | Suc of nat;;

let rec inc = function One -> Bit0 One
              | Bit0 x -> Bit1 x
              | Bit1 x -> Bit0 (inc x);;

let rec bit_int
  x0 n = match x0, n with Neg (Bit1 m), Suc n -> bit_int (Neg (inc m)) n
    | Neg (Bit0 m), Suc n -> bit_int (Neg m) n
    | Pos (Bit1 m), Suc n -> bit_int (Pos m) n
    | Pos (Bit0 m), Suc n -> bit_int (Pos m) n
    | Pos One, Suc n -> false
    | Neg (Bit1 m), Zero_nat -> true
    | Neg (Bit0 m), Zero_nat -> false
    | Pos (Bit1 m), Zero_nat -> true
    | Pos (Bit0 m), Zero_nat -> false
    | Pos One, Zero_nat -> true
    | Neg One, n -> true
    | Zero_int, n -> false;;

type 'a semiring_modulo_trivial =
  {divide_trivial_semiring_modulo_trivial : 'a divide_trivial;
    semiring_modulo_semiring_modulo_trivial : 'a semiring_modulo};;

type 'a semiring_bits =
  {semiring_parity_semiring_bits : 'a semiring_parity;
    semiring_modulo_trivial_semiring_bits : 'a semiring_modulo_trivial;
    bit : 'a -> nat -> bool};;
let bit _A = _A.bit;;

let semiring_modulo_trivial_int =
  ({divide_trivial_semiring_modulo_trivial = divide_trivial_int;
     semiring_modulo_semiring_modulo_trivial = semiring_modulo_int}
    : myint semiring_modulo_trivial);;

let semiring_bits_int =
  ({semiring_parity_semiring_bits = semiring_parity_int;
     semiring_modulo_trivial_semiring_bits = semiring_modulo_trivial_int;
     bit = bit_int}
    : myint semiring_bits);;

let rec push_bit_int
  x0 i = match x0, i with Suc n, i -> push_bit_int n (dup i)
    | Zero_nat, i -> i;;

let rec or_num x0 x1 = match x0, x1 with One, One -> One
                 | One, Bit0 n -> Bit1 n
                 | One, Bit1 n -> Bit1 n
                 | Bit0 m, One -> Bit1 m
                 | Bit0 m, Bit0 n -> Bit0 (or_num m n)
                 | Bit0 m, Bit1 n -> Bit1 (or_num m n)
                 | Bit1 m, One -> Bit1 m
                 | Bit1 m, Bit0 n -> Bit1 (or_num m n)
                 | Bit1 m, Bit1 n -> Bit1 (or_num m n);;

let rec numeral _A
  = function
    Bit1 n ->
      (let m = numeral _A n in
        plus _A.semigroup_add_numeral.plus_semigroup_add
          (plus _A.semigroup_add_numeral.plus_semigroup_add m m)
          (one _A.one_numeral))
    | Bit0 n ->
        (let m = numeral _A n in
          plus _A.semigroup_add_numeral.plus_semigroup_add m m)
    | One -> one _A.one_numeral;;

let rec suba _A
  k l = minus _A.group_add_neg_numeral.minus_group_add
          (numeral _A.numeral_neg_numeral k)
          (numeral _A.numeral_neg_numeral l);;

let rec not_int = function Neg n -> suba neg_numeral_int n One
                  | Pos n -> Neg (inc n)
                  | Zero_int -> uminus_inta one_inta;;

let rec map_option f x1 = match f, x1 with f, None -> None
                     | f, Some x2 -> Some (f x2);;

let rec and_not_num
  x0 x1 = match x0, x1 with One, One -> None
    | One, Bit0 n -> Some One
    | One, Bit1 n -> None
    | Bit0 m, One -> Some (Bit0 m)
    | Bit0 m, Bit0 n -> map_option (fun a -> Bit0 a) (and_not_num m n)
    | Bit0 m, Bit1 n -> map_option (fun a -> Bit0 a) (and_not_num m n)
    | Bit1 m, One -> Some (Bit0 m)
    | Bit1 m, Bit0 n ->
        (match and_not_num m n with None -> Some One
          | Some na -> Some (Bit1 na))
    | Bit1 m, Bit1 n -> map_option (fun a -> Bit0 a) (and_not_num m n);;

let rec or_not_num_neg x0 x1 = match x0, x1 with One, One -> One
                         | One, Bit0 m -> Bit1 m
                         | One, Bit1 m -> Bit1 m
                         | Bit0 n, One -> Bit0 One
                         | Bit0 n, Bit0 m -> bitM (or_not_num_neg n m)
                         | Bit0 n, Bit1 m -> Bit0 (or_not_num_neg n m)
                         | Bit1 n, One -> One
                         | Bit1 n, Bit0 m -> bitM (or_not_num_neg n m)
                         | Bit1 n, Bit1 m -> bitM (or_not_num_neg n m);;

let rec and_num
  x0 x1 = match x0, x1 with One, One -> Some One
    | One, Bit0 n -> None
    | One, Bit1 n -> Some One
    | Bit0 m, One -> None
    | Bit0 m, Bit0 n -> map_option (fun a -> Bit0 a) (and_num m n)
    | Bit0 m, Bit1 n -> map_option (fun a -> Bit0 a) (and_num m n)
    | Bit1 m, One -> Some One
    | Bit1 m, Bit0 n -> map_option (fun a -> Bit0 a) (and_num m n)
    | Bit1 m, Bit1 n ->
        (match and_num m n with None -> Some One | Some na -> Some (Bit1 na));;

let rec and_int
  i j = match i, j with
    Neg (Bit1 n), Pos m -> suba neg_numeral_int (or_not_num_neg (Bit0 n) m) One
    | Neg (Bit0 n), Pos m ->
        suba neg_numeral_int (or_not_num_neg (bitM n) m) One
    | Neg One, Pos m -> Pos m
    | Pos n, Neg (Bit1 m) ->
        suba neg_numeral_int (or_not_num_neg (Bit0 m) n) One
    | Pos n, Neg (Bit0 m) ->
        suba neg_numeral_int (or_not_num_neg (bitM m) n) One
    | Pos n, Neg One -> Pos n
    | Neg n, Neg m ->
        not_int
          (or_int (suba neg_numeral_int n One) (suba neg_numeral_int m One))
    | Pos n, Pos m ->
        (match and_num n m with None -> Zero_int | Some a -> Pos a)
    | i, Zero_int -> Zero_int
    | Zero_int, j -> Zero_int
and or_int
  i j = match i, j with
    Neg (Bit1 n), Pos m ->
      (match and_not_num (Bit0 n) m with None -> uminus_inta one_inta
        | Some na -> Neg (inc na))
    | Neg (Bit0 n), Pos m ->
        (match and_not_num (bitM n) m with None -> uminus_inta one_inta
          | Some na -> Neg (inc na))
    | Neg One, Pos m -> Neg One
    | Pos n, Neg (Bit1 m) ->
        (match and_not_num (Bit0 m) n with None -> uminus_inta one_inta
          | Some na -> Neg (inc na))
    | Pos n, Neg (Bit0 m) ->
        (match and_not_num (bitM m) n with None -> uminus_inta one_inta
          | Some na -> Neg (inc na))
    | Pos n, Neg One -> Neg One
    | Neg n, Neg m ->
        not_int
          (and_int (suba neg_numeral_int n One) (suba neg_numeral_int m One))
    | Pos n, Pos m -> Pos (or_num n m)
    | i, Zero_int -> i
    | Zero_int, j -> j;;

let rec unset_bit_int n k = and_int k (not_int (push_bit_int n one_inta));;

let rec power _A a x1 = match a, x1 with a, Zero_nat -> one _A.one_power
                   | a, Suc n -> times _A.times_power a (power _A a n);;

let rec take_bit_int n k = modulo_inta k (power power_int (Pos (Bit0 One)) n);;

let rec xor_num
  x0 x1 = match x0, x1 with One, One -> None
    | One, Bit0 n -> Some (Bit1 n)
    | One, Bit1 n -> Some (Bit0 n)
    | Bit0 m, One -> Some (Bit1 m)
    | Bit0 m, Bit0 n -> map_option (fun a -> Bit0 a) (xor_num m n)
    | Bit0 m, Bit1 n ->
        Some (match xor_num m n with None -> One | Some a -> Bit1 a)
    | Bit1 m, One -> Some (Bit0 m)
    | Bit1 m, Bit0 n ->
        Some (match xor_num m n with None -> One | Some a -> Bit1 a)
    | Bit1 m, Bit1 n -> map_option (fun a -> Bit0 a) (xor_num m n);;

let rec xor_int
  i j = match i, j with
    Pos n, Neg m -> not_int (xor_int (Pos n) (suba neg_numeral_int m One))
    | Neg n, Pos m -> not_int (xor_int (suba neg_numeral_int n One) (Pos m))
    | Neg n, Neg m ->
        xor_int (suba neg_numeral_int n One) (suba neg_numeral_int m One)
    | Pos n, Pos m ->
        (match xor_num n m with None -> Zero_int | Some a -> Pos a)
    | i, Zero_int -> i
    | Zero_int, j -> j;;

let rec flip_bit_int n k = xor_int k (push_bit_int n one_inta);;

let rec drop_bit_int
  x0 i = match x0, i with Suc n, Neg (Bit1 m) -> drop_bit_int n (Neg (inc m))
    | Suc n, Neg (Bit0 m) -> drop_bit_int n (Neg m)
    | Suc n, Neg One -> uminus_inta one_inta
    | Suc n, Pos (Bit1 m) -> drop_bit_int n (Pos m)
    | Suc n, Pos (Bit0 m) -> drop_bit_int n (Pos m)
    | Suc n, Pos One -> Zero_int
    | Suc n, Zero_int -> Zero_int
    | Zero_nat, i -> i;;

let rec set_bit_int n k = or_int k (push_bit_int n one_inta);;

let rec mask_int n = minus_inta (power power_int (Pos (Bit0 One)) n) one_inta;;

type 'a semiring_bit_operations =
  {semiring_bits_semiring_bit_operations : 'a semiring_bits;
    anda : 'a -> 'a -> 'a; ora : 'a -> 'a -> 'a; xor : 'a -> 'a -> 'a;
    mask : nat -> 'a; set_bit : nat -> 'a -> 'a; unset_bit : nat -> 'a -> 'a;
    flip_bit : nat -> 'a -> 'a; push_bit : nat -> 'a -> 'a;
    drop_bit : nat -> 'a -> 'a; take_bit : nat -> 'a -> 'a};;
let anda _A = _A.anda;;
let ora _A = _A.ora;;
let xor _A = _A.xor;;
let mask _A = _A.mask;;
let set_bit _A = _A.set_bit;;
let unset_bit _A = _A.unset_bit;;
let flip_bit _A = _A.flip_bit;;
let push_bit _A = _A.push_bit;;
let drop_bit _A = _A.drop_bit;;
let take_bit _A = _A.take_bit;;

type 'a ring_bit_operations =
  {semiring_bit_operations_ring_bit_operations : 'a semiring_bit_operations;
    ring_parity_ring_bit_operations : 'a ring_parity; nota : 'a -> 'a};;
let nota _A = _A.nota;;

let semiring_bit_operations_int =
  ({semiring_bits_semiring_bit_operations = semiring_bits_int; anda = and_int;
     ora = or_int; xor = xor_int; mask = mask_int; set_bit = set_bit_int;
     unset_bit = unset_bit_int; flip_bit = flip_bit_int;
     push_bit = push_bit_int; drop_bit = drop_bit_int; take_bit = take_bit_int}
    : myint semiring_bit_operations);;

let ring_bit_operations_int =
  ({semiring_bit_operations_ring_bit_operations = semiring_bit_operations_int;
     ring_parity_ring_bit_operations = ring_parity_int; nota = not_int}
    : myint ring_bit_operations);;

type 'a itself = Type;;

type 'a len0 = {len_of : 'a itself -> nat};;
let len_of _A = _A.len_of;;

type 'a len = {len0_len : 'a len0};;

type 'a word = Word of myint;;

let rec one_worda _A = Word one_inta;;

let rec one_word _A = ({one = one_worda _A} : 'a word one);;

let rec the_int _A (Word x) = x;;

let rec of_int _A k = Word (take_bit_int (len_of _A.len0_len Type) k);;

let rec times_worda _A
  a b = of_int _A (times_inta (the_int _A a) (the_int _A b));;

let rec times_word _A = ({times = times_worda _A} : 'a word times);;

let rec power_word _A =
  ({one_power = (one_word _A); times_power = (times_word _A)} : 'a word power);;

type crbit = ZF | CF | PF | SF | OF;;

let rec equal_crbit x0 x1 = match x0, x1 with SF, OF -> false
                      | OF, SF -> false
                      | PF, OF -> false
                      | OF, PF -> false
                      | PF, SF -> false
                      | SF, PF -> false
                      | CF, OF -> false
                      | OF, CF -> false
                      | CF, SF -> false
                      | SF, CF -> false
                      | CF, PF -> false
                      | PF, CF -> false
                      | ZF, OF -> false
                      | OF, ZF -> false
                      | ZF, SF -> false
                      | SF, ZF -> false
                      | ZF, PF -> false
                      | PF, ZF -> false
                      | ZF, CF -> false
                      | CF, ZF -> false
                      | OF, OF -> true
                      | SF, SF -> true
                      | PF, PF -> true
                      | CF, CF -> true
                      | ZF, ZF -> true;;

type ireg = RAX | RBX | RCX | RDX | RSI | RDI | RBP | RSP | R8 | R9 | R10 | R11
  | R12 | R13 | R14 | R15;;

let rec equal_ireg x0 x1 = match x0, x1 with R14, R15 -> false
                     | R15, R14 -> false
                     | R13, R15 -> false
                     | R15, R13 -> false
                     | R13, R14 -> false
                     | R14, R13 -> false
                     | R12, R15 -> false
                     | R15, R12 -> false
                     | R12, R14 -> false
                     | R14, R12 -> false
                     | R12, R13 -> false
                     | R13, R12 -> false
                     | R11, R15 -> false
                     | R15, R11 -> false
                     | R11, R14 -> false
                     | R14, R11 -> false
                     | R11, R13 -> false
                     | R13, R11 -> false
                     | R11, R12 -> false
                     | R12, R11 -> false
                     | R10, R15 -> false
                     | R15, R10 -> false
                     | R10, R14 -> false
                     | R14, R10 -> false
                     | R10, R13 -> false
                     | R13, R10 -> false
                     | R10, R12 -> false
                     | R12, R10 -> false
                     | R10, R11 -> false
                     | R11, R10 -> false
                     | R9, R15 -> false
                     | R15, R9 -> false
                     | R9, R14 -> false
                     | R14, R9 -> false
                     | R9, R13 -> false
                     | R13, R9 -> false
                     | R9, R12 -> false
                     | R12, R9 -> false
                     | R9, R11 -> false
                     | R11, R9 -> false
                     | R9, R10 -> false
                     | R10, R9 -> false
                     | R8, R15 -> false
                     | R15, R8 -> false
                     | R8, R14 -> false
                     | R14, R8 -> false
                     | R8, R13 -> false
                     | R13, R8 -> false
                     | R8, R12 -> false
                     | R12, R8 -> false
                     | R8, R11 -> false
                     | R11, R8 -> false
                     | R8, R10 -> false
                     | R10, R8 -> false
                     | R8, R9 -> false
                     | R9, R8 -> false
                     | RSP, R15 -> false
                     | R15, RSP -> false
                     | RSP, R14 -> false
                     | R14, RSP -> false
                     | RSP, R13 -> false
                     | R13, RSP -> false
                     | RSP, R12 -> false
                     | R12, RSP -> false
                     | RSP, R11 -> false
                     | R11, RSP -> false
                     | RSP, R10 -> false
                     | R10, RSP -> false
                     | RSP, R9 -> false
                     | R9, RSP -> false
                     | RSP, R8 -> false
                     | R8, RSP -> false
                     | RBP, R15 -> false
                     | R15, RBP -> false
                     | RBP, R14 -> false
                     | R14, RBP -> false
                     | RBP, R13 -> false
                     | R13, RBP -> false
                     | RBP, R12 -> false
                     | R12, RBP -> false
                     | RBP, R11 -> false
                     | R11, RBP -> false
                     | RBP, R10 -> false
                     | R10, RBP -> false
                     | RBP, R9 -> false
                     | R9, RBP -> false
                     | RBP, R8 -> false
                     | R8, RBP -> false
                     | RBP, RSP -> false
                     | RSP, RBP -> false
                     | RDI, R15 -> false
                     | R15, RDI -> false
                     | RDI, R14 -> false
                     | R14, RDI -> false
                     | RDI, R13 -> false
                     | R13, RDI -> false
                     | RDI, R12 -> false
                     | R12, RDI -> false
                     | RDI, R11 -> false
                     | R11, RDI -> false
                     | RDI, R10 -> false
                     | R10, RDI -> false
                     | RDI, R9 -> false
                     | R9, RDI -> false
                     | RDI, R8 -> false
                     | R8, RDI -> false
                     | RDI, RSP -> false
                     | RSP, RDI -> false
                     | RDI, RBP -> false
                     | RBP, RDI -> false
                     | RSI, R15 -> false
                     | R15, RSI -> false
                     | RSI, R14 -> false
                     | R14, RSI -> false
                     | RSI, R13 -> false
                     | R13, RSI -> false
                     | RSI, R12 -> false
                     | R12, RSI -> false
                     | RSI, R11 -> false
                     | R11, RSI -> false
                     | RSI, R10 -> false
                     | R10, RSI -> false
                     | RSI, R9 -> false
                     | R9, RSI -> false
                     | RSI, R8 -> false
                     | R8, RSI -> false
                     | RSI, RSP -> false
                     | RSP, RSI -> false
                     | RSI, RBP -> false
                     | RBP, RSI -> false
                     | RSI, RDI -> false
                     | RDI, RSI -> false
                     | RDX, R15 -> false
                     | R15, RDX -> false
                     | RDX, R14 -> false
                     | R14, RDX -> false
                     | RDX, R13 -> false
                     | R13, RDX -> false
                     | RDX, R12 -> false
                     | R12, RDX -> false
                     | RDX, R11 -> false
                     | R11, RDX -> false
                     | RDX, R10 -> false
                     | R10, RDX -> false
                     | RDX, R9 -> false
                     | R9, RDX -> false
                     | RDX, R8 -> false
                     | R8, RDX -> false
                     | RDX, RSP -> false
                     | RSP, RDX -> false
                     | RDX, RBP -> false
                     | RBP, RDX -> false
                     | RDX, RDI -> false
                     | RDI, RDX -> false
                     | RDX, RSI -> false
                     | RSI, RDX -> false
                     | RCX, R15 -> false
                     | R15, RCX -> false
                     | RCX, R14 -> false
                     | R14, RCX -> false
                     | RCX, R13 -> false
                     | R13, RCX -> false
                     | RCX, R12 -> false
                     | R12, RCX -> false
                     | RCX, R11 -> false
                     | R11, RCX -> false
                     | RCX, R10 -> false
                     | R10, RCX -> false
                     | RCX, R9 -> false
                     | R9, RCX -> false
                     | RCX, R8 -> false
                     | R8, RCX -> false
                     | RCX, RSP -> false
                     | RSP, RCX -> false
                     | RCX, RBP -> false
                     | RBP, RCX -> false
                     | RCX, RDI -> false
                     | RDI, RCX -> false
                     | RCX, RSI -> false
                     | RSI, RCX -> false
                     | RCX, RDX -> false
                     | RDX, RCX -> false
                     | RBX, R15 -> false
                     | R15, RBX -> false
                     | RBX, R14 -> false
                     | R14, RBX -> false
                     | RBX, R13 -> false
                     | R13, RBX -> false
                     | RBX, R12 -> false
                     | R12, RBX -> false
                     | RBX, R11 -> false
                     | R11, RBX -> false
                     | RBX, R10 -> false
                     | R10, RBX -> false
                     | RBX, R9 -> false
                     | R9, RBX -> false
                     | RBX, R8 -> false
                     | R8, RBX -> false
                     | RBX, RSP -> false
                     | RSP, RBX -> false
                     | RBX, RBP -> false
                     | RBP, RBX -> false
                     | RBX, RDI -> false
                     | RDI, RBX -> false
                     | RBX, RSI -> false
                     | RSI, RBX -> false
                     | RBX, RDX -> false
                     | RDX, RBX -> false
                     | RBX, RCX -> false
                     | RCX, RBX -> false
                     | RAX, R15 -> false
                     | R15, RAX -> false
                     | RAX, R14 -> false
                     | R14, RAX -> false
                     | RAX, R13 -> false
                     | R13, RAX -> false
                     | RAX, R12 -> false
                     | R12, RAX -> false
                     | RAX, R11 -> false
                     | R11, RAX -> false
                     | RAX, R10 -> false
                     | R10, RAX -> false
                     | RAX, R9 -> false
                     | R9, RAX -> false
                     | RAX, R8 -> false
                     | R8, RAX -> false
                     | RAX, RSP -> false
                     | RSP, RAX -> false
                     | RAX, RBP -> false
                     | RBP, RAX -> false
                     | RAX, RDI -> false
                     | RDI, RAX -> false
                     | RAX, RSI -> false
                     | RSI, RAX -> false
                     | RAX, RDX -> false
                     | RDX, RAX -> false
                     | RAX, RCX -> false
                     | RCX, RAX -> false
                     | RAX, RBX -> false
                     | RBX, RAX -> false
                     | R15, R15 -> true
                     | R14, R14 -> true
                     | R13, R13 -> true
                     | R12, R12 -> true
                     | R11, R11 -> true
                     | R10, R10 -> true
                     | R9, R9 -> true
                     | R8, R8 -> true
                     | RSP, RSP -> true
                     | RBP, RBP -> true
                     | RDI, RDI -> true
                     | RSI, RSI -> true
                     | RDX, RDX -> true
                     | RCX, RCX -> true
                     | RBX, RBX -> true
                     | RAX, RAX -> true;;

type preg = PC | IR of ireg | CR of crbit;;

let rec equal_prega x0 x1 = match x0, x1 with IR x2, CR x3 -> false
                      | CR x3, IR x2 -> false
                      | PC, CR x3 -> false
                      | CR x3, PC -> false
                      | PC, IR x2 -> false
                      | IR x2, PC -> false
                      | CR x3, CR y3 -> equal_crbit x3 y3
                      | IR x2, IR y2 -> equal_ireg x2 y2
                      | PC, PC -> true;;

type 'a equal = {equal : 'a -> 'a -> bool};;
let equal _A = _A.equal;;

let equal_preg = ({equal = equal_prega} : preg equal);;

let rec plus_nat x0 n = match x0, n with Suc m, n -> plus_nat m (Suc n)
                   | Zero_nat, n -> n;;

let rec times_nat x0 n = match x0, n with Zero_nat, n -> Zero_nat
                    | Suc m, n -> plus_nat n (times_nat m n);;

let one_nat : nat = Suc Zero_nat;;

let rec nat_of_num
  = function Bit1 n -> (let m = nat_of_num n in Suc (plus_nat m m))
    | Bit0 n -> (let m = nat_of_num n in plus_nat m m)
    | One -> one_nat;;

type 'a finite = unit;;

type 'a bit0 = Abs_bit0 of myint;;

let rec len_of_bit0 _A uu = times_nat (nat_of_num (Bit0 One)) (len_of _A Type);;

let rec len0_bit0 _A = ({len_of = len_of_bit0 _A} : 'a bit0 len0);;

let rec len_bit0 _A = ({len0_len = (len0_bit0 _A.len0_len)} : 'a bit0 len);;

type num1 = One_num1;;

let rec len_of_num1 uu = one_nat;;

let len0_num1 = ({len_of = len_of_num1} : num1 len0);;

let len_num1 = ({len0_len = len0_num1} : num1 len);;

type 'a signed = EMPTY__;;

let rec len_of_signed _A x = len_of _A Type;;

let rec len0_signed _A = ({len_of = len_of_signed _A} : 'a signed len0);;

let rec len_signed _A =
  ({len0_len = (len0_signed _A.len0_len)} : 'a signed len);;

type vala = Vundef | Vbyte of num1 bit0 bit0 bit0 word |
  Vshort of num1 bit0 bit0 bit0 bit0 word |
  Vint of num1 bit0 bit0 bit0 bit0 bit0 word |
  Vlong of num1 bit0 bit0 bit0 bit0 bit0 bit0 word;;

type comparison = Ceq | Cne | Clt | Cle | Cgt | Cge;;

type memory_chunk = M8 | M16 | M32 | M64;;

type addrmode =
  Addrmode of
    ireg option * (ireg * num1 bit0 bit0 bit0 word) option *
      num1 bit0 bit0 bit0 bit0 bit0 word;;

type testcond = Cond_e | Cond_ne | Cond_b | Cond_be | Cond_ae | Cond_a | Cond_l
  | Cond_le | Cond_ge | Cond_g | Cond_p | Cond_np;;

type outcome =
  Next of
    (preg -> vala) *
      (num1 bit0 bit0 bit0 bit0 bit0 bit0 word ->
        num1 bit0 bit0 bit0 word option)
  | Stuck;;

type bit_mode = D64 | D32 | D16;;

type instruction = Pmovl_rr of ireg * ireg | Pmovq_rr of ireg * ireg |
  Pmovl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pmovq_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 bit0 word |
  Pmov_rm of ireg * addrmode * memory_chunk |
  Pmov_mr of addrmode * ireg * memory_chunk |
  Pmov_mi of addrmode * num1 bit0 bit0 bit0 bit0 bit0 word * memory_chunk |
  Pcmovl of testcond * ireg * ireg | Pcmovq of testcond * ireg * ireg |
  Pxchgq_rr of ireg * ireg | Pxchgq_rm of ireg * addrmode * memory_chunk |
  Pmovsl_rr of ireg * ireg | Pcdq | Pcqo | Pleaq of ireg * addrmode |
  Pnegl of ireg | Pnegq of ireg | Paddq_rr of ireg * ireg |
  Paddl_rr of ireg * ireg |
  Paddl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Paddw_ri of ireg * num1 bit0 bit0 bit0 bit0 word |
  Paddq_mi of addrmode * num1 bit0 bit0 bit0 bit0 bit0 word * memory_chunk |
  Psubl_rr of ireg * ireg | Psubq_rr of ireg * ireg |
  Psubl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word | Pmull_r of ireg |
  Pmulq_r of ireg | Pimull_r of ireg | Pimulq_r of ireg | Pdivl_r of ireg |
  Pdivq_r of ireg | Pidivl_r of ireg | Pidivq_r of ireg |
  Pandl_rr of ireg * ireg |
  Pandl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pandq_rr of ireg * ireg | Porl_rr of ireg * ireg |
  Porl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word | Porq_rr of ireg * ireg
  | Pxorl_rr of ireg * ireg | Pxorq_rr of ireg * ireg |
  Pxorl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pshll_ri of ireg * num1 bit0 bit0 bit0 word |
  Pshlq_ri of ireg * num1 bit0 bit0 bit0 word | Pshll_r of ireg |
  Pshlq_r of ireg | Pshrl_ri of ireg * num1 bit0 bit0 bit0 word |
  Pshrq_ri of ireg * num1 bit0 bit0 bit0 word | Pshrl_r of ireg |
  Pshrq_r of ireg | Psarl_ri of ireg * num1 bit0 bit0 bit0 word |
  Psarq_ri of ireg * num1 bit0 bit0 bit0 word | Psarl_r of ireg |
  Psarq_r of ireg | Prolw_ri of ireg * num1 bit0 bit0 bit0 word |
  Prorl_ri of ireg * num1 bit0 bit0 bit0 word |
  Prorq_ri of ireg * num1 bit0 bit0 bit0 word | Pbswapl of ireg |
  Pbswapq of ireg | Ppushl_r of ireg |
  Ppushl_i of num1 bit0 bit0 bit0 bit0 bit0 word |
  Ppushq_m of addrmode * memory_chunk | Ppopl of ireg | Ptestl_rr of ireg * ireg
  | Ptestq_rr of ireg * ireg |
  Ptestl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Ptestq_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pcmpl_rr of ireg * ireg | Pcmpq_rr of ireg * ireg |
  Pcmpl_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pcmpq_ri of ireg * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pjcc of testcond * num1 bit0 bit0 bit0 bit0 bit0 word |
  Pjmp of num1 bit0 bit0 bit0 bit0 bit0 word | Pcall_r of ireg |
  Pcall_i of num1 bit0 bit0 bit0 bit0 bit0 word | Pret | Pnop | P;;

let rec eq _A a b = equal _A a b;;

let rec nat = function Pos k -> nat_of_num k
              | Zero_int -> Zero_nat
              | Neg k -> Zero_nat;;

let rec nth x0 x1 = match x0, x1 with x :: xs, Suc n -> nth xs n
              | x :: xs, Zero_nat -> x;;

let rec zero_word _A = Word Zero_int;;

let rec of_optbool
  ob = (match ob with None -> Vundef
         | Some true ->
           Vint (one_worda
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         | Some false ->
           Vint (zero_word
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))));;

let rec less_eq_word _A a b = less_eq_int (the_int _A a) (the_int _A b);;

let rec equal_word _A v w = equal_int (the_int _A v) (the_int _A w);;

let rec less_word _A a b = less_int (the_int _A a) (the_int _A b);;

let rec cmpu32
  c x y =
    (match c
      with Ceq ->
        equal_word
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x y
      | Cne ->
        not (equal_word
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x
              y)
      | Clt ->
        less_word
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x y
      | Cle ->
        less_eq_word
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x y
      | Cgt ->
        less_word
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) y x
      | Cge ->
        less_eq_word
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) y x);;

let rec cmpu_bool
  c v1 v2 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint n1 ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint n2 -> Some (cmpu32 c n1 n2) | Vlong _ -> None)
      | Vlong _ -> None);;

let rec cmpu c v1 v2 = of_optbool (cmpu_bool c v1 v2);;

let rec or_word _A v w = Word (or_int (the_int _A v) (the_int _A w));;

let rec or32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (or_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec or64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (or_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec plus_word _A a b = of_int _A (plus_inta (the_int _A a) (the_int _A b));;

let rec push_bit_word _A
  n w = times_worda _A w
          (power (power_word _A) (of_int _A (Pos (Bit0 One))) n);;

let rec cast _B _A
  w = Word (take_bit_int (len_of _A.len0_len Type) (the_int _B w));;

let rec option_u64_of_u8_8
  v0 v1 v2 v3 v4 v5 v6 v7 =
    (match v0 with None -> None
      | Some n0 ->
        (match v1 with None -> None
          | Some n1 ->
            (match v2 with None -> None
              | Some n2 ->
                (match v3 with None -> None
                  | Some n3 ->
                    (match v4 with None -> None
                      | Some n4 ->
                        (match v5 with None -> None
                          | Some n5 ->
                            (match v6 with None -> None
                              | Some n6 ->
                                (match v7 with None -> None
                                  | Some n7 ->
                                    Some (or_word
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   (push_bit_word
     (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
     (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
     (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
       (len_bit0
         (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
       n7))
   (or_word
     (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
     (push_bit_word
       (len_bit0
         (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
       (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))
       (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (len_bit0
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         n6))
     (or_word
       (len_bit0
         (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
       (push_bit_word
         (len_bit0
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
         (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (len_bit0
             (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
           n5))
       (or_word
         (len_bit0
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         (push_bit_word
           (len_bit0
             (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
           (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
           (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
             (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
             n4))
         (or_word
           (len_bit0
             (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
           (push_bit_word
             (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
             (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
             (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               n3))
           (or_word
             (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
             (push_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One)))))
               (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n2))
             (or_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (push_bit_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                 (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   n1))
               (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n0))))))))))))))));;

let rec option_u64_of_u8_4
  v0 v1 v2 v3 =
    (match v0 with None -> None
      | Some n0 ->
        (match v1 with None -> None
          | Some n1 ->
            (match v2 with None -> None
              | Some n2 ->
                (match v3 with None -> None
                  | Some n3 ->
                    Some (or_word
                           (len_bit0
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                           (push_bit_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                             (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
                             (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (len_bit0
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1))))))
                               n3))
                           (or_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                             (push_bit_word
                               (len_bit0
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1))))))
                               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One)))))
                               (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))))
                                 n2))
                             (or_word
                               (len_bit0
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1))))))
                               (push_bit_word
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))))
                                 (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                                 (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                   n1))
                               (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))))
                                 n0))))))));;

let rec option_u64_of_u8_2
  v0 v1 =
    (match v0 with None -> None
      | Some n0 ->
        (match v1 with None -> None
          | Some n1 ->
            Some (or_word
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (push_bit_word
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                     (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (len_bit0
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                       n1))
                   (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     n0))));;

let rec option_u64_of_u8_1
  v0 = (match v0 with None -> None
         | Some v ->
           Some (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  v));;

let rec memory_chunk_value_of_u64
  mc v =
    (match mc
      with M8 ->
        Vbyte (cast (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                (len_bit0 (len_bit0 (len_bit0 len_num1))) v)
      | M16 ->
        Vshort
          (cast (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))) v)
      | M32 ->
        Vint (cast (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               v)
      | M64 ->
        Vlong (cast (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                v));;

let rec option_val_of_u64
  mc v =
    (match v with None -> None
      | Some v1 -> Some (memory_chunk_value_of_u64 mc v1));;

let rec loadv
  mc m addr =
    option_val_of_u64 mc
      (match mc with M8 -> option_u64_of_u8_1 (m addr)
        | M16 ->
          option_u64_of_u8_2 (m addr)
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (one_worda
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))))
        | M32 ->
          option_u64_of_u8_4 (m addr)
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (one_worda
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit0 One)))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit1 One)))))
        | M64 ->
          option_u64_of_u8_8 (m addr)
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (one_worda
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit0 One)))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit1 One)))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit0 (Bit0 One))))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit1 (Bit0 One))))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit0 (Bit1 One))))))
            (m (plus_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 addr
                 (of_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (Pos (Bit1 (Bit1 One)))))));;

let rec add16
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef
      | Vshort n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef
          | Vshort n2 ->
            Vshort
              (plus_word (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))) n1
                n2)
          | Vint _ -> Vundef | Vlong _ -> Vundef)
      | Vint _ -> Vundef | Vlong _ -> Vundef);;

let rec add32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (plus_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec add64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (plus_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec and_word _A v w = Word (and_int (the_int _A v) (the_int _A w));;

let rec and32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (and_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec and64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (and_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec cmpu64
  c x y =
    (match c
      with Ceq ->
        equal_word
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          x y
      | Cne ->
        not (equal_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              x y)
      | Clt ->
        less_word
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          x y
      | Cle ->
        less_eq_word
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          x y
      | Cgt ->
        less_word
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          y x
      | Cge ->
        less_eq_word
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          y x);;

let rec cmplu_bool
  c v1 v2 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint _ -> None
      | Vlong n1 ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint _ -> None | Vlong n2 -> Some (cmpu64 c n1 n2)));;

let rec cmplu c v1 v2 = of_optbool (cmplu_bool c v1 v2);;

let rec signed_take_bit _A
  n a = (let l =
           take_bit _A.semiring_bit_operations_ring_bit_operations (Suc n) a in
          (if bit _A.semiring_bit_operations_ring_bit_operations.semiring_bits_semiring_bit_operations
                l n
            then plus _A.ring_parity_ring_bit_operations.comm_ring_1_ring_parity.ring_1_comm_ring_1.neg_numeral_ring_1.numeral_neg_numeral.semigroup_add_numeral.plus_semigroup_add
                   l (push_bit _A.semiring_bit_operations_ring_bit_operations
                       (Suc n)
                       (uminus
                         _A.ring_parity_ring_bit_operations.comm_ring_1_ring_parity.ring_1_comm_ring_1.neg_numeral_ring_1.group_add_neg_numeral.uminus_group_add
                         (one _A.ring_parity_ring_bit_operations.comm_ring_1_ring_parity.ring_1_comm_ring_1.neg_numeral_ring_1.numeral_neg_numeral.one_numeral)))
            else l));;

let rec minus_nat m n = match m, n with Suc m, Suc n -> minus_nat m n
                    | Zero_nat, n -> Zero_nat
                    | m, Zero_nat -> m;;

let rec the_signed_int _A
  w = signed_take_bit ring_bit_operations_int
        (minus_nat (len_of _A.len0_len Type) (Suc Zero_nat)) (the_int _A w);;

let rec msb32
  x = less_int
        (the_signed_int
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x)
        Zero_int;;

let rec msb64
  x = less_int
        (the_signed_int
          (len_bit0
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          x)
        Zero_int;;

let rec mul32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (times_worda
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec mul64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (times_worda
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec uminus_word _A a = of_int _A (uminus_inta (the_int _A a));;

let rec neg32
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint n ->
          Vint (uminus_word
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 n)
        | Vlong _ -> Vundef);;

let rec neg64
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint _ -> Vundef
        | Vlong n ->
          Vlong (uminus_word
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  n));;

let rec drop_bit_word _A n w = Word (drop_bit_int n (the_int _A w));;

let rec modulo_word _A
  a b = of_int _A (modulo_inta (the_int _A a) (the_int _A b));;

let rec minus_word _A
  a b = of_int _A (minus_inta (the_int _A a) (the_int _A b));;

let rec the_nat _A w = nat (the_int _A w);;

let rec rol16
  v n = (match v with Vundef -> Vundef | Vbyte _ -> Vundef
          | Vshort v1 ->
            (match n with Vundef -> Vundef
              | Vbyte n1 ->
                (let n1a =
                   modulo_word (len_bit0 (len_bit0 (len_bit0 len_num1))) n1
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit0 (Bit0 (Bit0 (Bit0 One))))))
                   in
                  Vshort
                    (or_word
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      (push_bit_word
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1))) n1a)
                        v1)
                      (drop_bit_word
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (minus_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit0 (Bit0 (Bit0 One))))))
                            n1a))
                        v1)))
              | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef)
          | Vint _ -> Vundef | Vlong _ -> Vundef);;

let rec ror32
  v n = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint v1 ->
            (match n with Vundef -> Vundef
              | Vbyte n1 ->
                (let n1a =
                   modulo_word (len_bit0 (len_bit0 (len_bit0 len_num1))) n1
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
                   in
                  Vint (or_word
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (drop_bit_word
                           (len_bit0
                             (len_bit0
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                           (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             n1a)
                           v1)
                         (push_bit_word
                           (len_bit0
                             (len_bit0
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                           (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (minus_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
                               n1a))
                           v1)))
              | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef)
          | Vlong _ -> Vundef);;

let rec ror64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let n2a =
               modulo_word (len_bit0 (len_bit0 (len_bit0 len_num1))) n2
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
              Vlong (or_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (drop_bit_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1))) n2a)
                        n1)
                      (push_bit_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (minus_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                            n2a))
                        n1)))
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef));;

let rec equal_nat x0 x1 = match x0, x1 with Zero_nat, Suc x2 -> false
                    | Suc x2, Zero_nat -> false
                    | Suc x2, Suc y2 -> equal_nat x2 y2
                    | Zero_nat, Zero_nat -> true;;

let rec less_nat m x1 = match m, x1 with m, Suc n -> less_eq_nat m n
                   | n, Zero_nat -> false
and less_eq_nat x0 n = match x0, n with Suc m, n -> less_nat m n
                  | Zero_nat, n -> true;;

let rec divmod_nat
  m n = (if equal_nat n Zero_nat || less_nat m n then (Zero_nat, m)
          else (let (q, a) = divmod_nat (minus_nat m n) n in (Suc q, a)));;

let rec modulo_nat m n = snd (divmod_nat m n);;

let rec cl_mask3
  w = modulo_nat (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1))) w)
        (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))));;

let rec sar32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask3 n2 in
             let a =
               of_int
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 (divide_inta
                   (the_signed_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     n1)
                   (power power_int (Pos (Bit0 One)) s))
               in
              Vint a)
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec cl_mask6
  w = modulo_nat (the_nat (len_bit0 (len_bit0 (len_bit0 len_num1))) w)
        (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))));;

let rec sar64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask6 n2 in
             let a =
               of_int
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (divide_inta
                   (the_signed_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     n1)
                   (power power_int (Pos (Bit0 One)) s))
               in
              Vlong a)
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef));;

let rec sdiv0
  x y = (if equal_int y Zero_int then Zero_int
          else (if less_eq_int Zero_int x && less_int Zero_int y ||
                     less_eq_int x Zero_int && less_int y Zero_int
                 then divide_inta x y
                 else uminus_inta (divide_inta (uminus_inta x) y)));;

let rec shl32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask3 n2 in
              Vint (push_bit_word
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     s n1))
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec shl64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask6 n2 in
              Vlong (push_bit_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      s n1))
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef));;

let rec shr32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask3 n2 in
              Vint (drop_bit_word
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     s n1))
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec shr64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef
          | Vbyte n2 ->
            (let s = cl_mask6 n2 in
              Vlong (drop_bit_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      s n1))
          | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong _ -> Vundef));;

let rec smod0 x y = minus_inta x (times_inta (sdiv0 x y) y);;

let rec sub32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (minus_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec sub64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (minus_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec xor_word _A v w = Word (xor_int (the_int _A v) (the_int _A w));;

let rec xor32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (xor_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n1 n2)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec xor64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vlong (xor_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    n1 n2)));;

let rec u8_list_of_u64
  i = [cast (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (and_word
           (len_bit0
             (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
           i (of_int
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 One)))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One)))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One)))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            (drop_bit_word
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 One)))))) i)
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))];;

let rec u8_list_of_u32
  i = [cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
         (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (and_word
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) i
           (of_int
             (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
             (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
            (drop_bit_word
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (nat_of_num (Bit0 (Bit0 (Bit0 One)))) i)
            (of_int
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
            (drop_bit_word
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One))))) i)
            (of_int
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word
            (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
            (drop_bit_word
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One))))) i)
            (of_int
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))];;

let rec u8_list_of_u16
  i = [cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
         (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (and_word (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))) i
           (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
             (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))));
        cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (and_word (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
            (drop_bit_word (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
              (nat_of_num (Bit0 (Bit0 (Bit0 One)))) i)
            (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
              (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))];;

let rec storev
  mc m addr v =
    (match mc
      with M8 ->
        (match v with Vundef -> None
          | Vbyte n ->
            Some (fun i ->
                   (if equal_word
                         (len_bit0
                           (len_bit0
                             (len_bit0
                               (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                         i addr
                     then Some n else m i))
          | Vshort _ -> None | Vint _ -> None | Vlong _ -> None)
      | M16 ->
        (match v with Vundef -> None | Vbyte _ -> None
          | Vshort n ->
            (let l = u8_list_of_u16 n in
              Some (fun i ->
                     (if equal_word
                           (len_bit0
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                           i addr
                       then Some (nth l Zero_nat)
                       else (if equal_word
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  i (plus_word
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                      addr
                                      (one_worda
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                              then Some (nth l one_nat) else m i))))
          | Vint _ -> None | Vlong _ -> None)
      | M32 ->
        (match v with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint n ->
            (let l = u8_list_of_u32 n in
              Some (fun i ->
                     (if equal_word
                           (len_bit0
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                           i addr
                       then Some (nth l Zero_nat)
                       else (if equal_word
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  i (plus_word
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                      addr
                                      (one_worda
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                              then Some (nth l one_nat)
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) i
 (plus_word
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   addr
   (of_int
     (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
     (Pos (Bit0 One))))
                                     then Some (nth l (nat_of_num (Bit0 One)))
                                     else (if equal_word
        (len_bit0
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
        i (plus_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            addr
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 One))))
    then Some (nth l (nat_of_num (Bit1 One))) else m i))))))
          | Vlong _ -> None)
      | M64 ->
        (match v with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint _ -> None
          | Vlong n ->
            (let l = u8_list_of_u64 n in
              Some (fun i ->
                     (if equal_word
                           (len_bit0
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                           i addr
                       then Some (nth l Zero_nat)
                       else (if equal_word
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  i (plus_word
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                      addr
                                      (one_worda
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                              then Some (nth l one_nat)
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) i
 (plus_word
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   addr
   (of_int
     (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
     (Pos (Bit0 One))))
                                     then Some (nth l (nat_of_num (Bit0 One)))
                                     else (if equal_word
        (len_bit0
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
        i (plus_word
            (len_bit0
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
            addr
            (of_int
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              (Pos (Bit1 One))))
    then Some (nth l (nat_of_num (Bit1 One)))
    else (if equal_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               i (plus_word
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   addr
                   (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 One)))))
           then Some (nth l (nat_of_num (Bit0 (Bit0 One))))
           else (if equal_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      i (plus_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          addr
                          (of_int
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (Pos (Bit1 (Bit0 One)))))
                  then Some (nth l (nat_of_num (Bit1 (Bit0 One))))
                  else (if equal_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                             i (plus_word
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))))
                                 addr
                                 (of_int
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                   (Pos (Bit0 (Bit1 One)))))
                         then Some (nth l (nat_of_num (Bit0 (Bit1 One))))
                         else (if equal_word
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                    i (plus_word
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) addr
(of_int
  (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
  (Pos (Bit1 (Bit1 One)))))
                                then Some (nth l (nat_of_num (Bit1 (Bit1 One))))
                                else m i))))))))))));;

let rec fun_upd _A f a b = (fun x -> (if eq _A x a then b else f x));;

let rec bswap32
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint n ->
          (let byte0 =
             push_bit_word
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
               (and_word
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 n (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (Pos (Bit1 (Bit1 (Bit1
(Bit1 (Bit1 (Bit1 (Bit1 One))))))))))
             in
           let byte1 =
             push_bit_word
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (nat_of_num (Bit0 (Bit0 (Bit0 One))))
               (and_word
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 n (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 (Bit1
    (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))
             in
           let byte2 =
             drop_bit_word
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (nat_of_num (Bit0 (Bit0 (Bit0 One))))
               (and_word
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 n (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit1
  (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))
             in
           let byte3 =
             drop_bit_word
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
               (and_word
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 n (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1
(Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))))))))))
             in
            Vint (or_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   (or_word
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (or_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                       byte0 byte1)
                     byte2)
                   byte3))
        | Vlong _ -> Vundef);;

let rec bswap64
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint _ -> Vundef
        | Vlong n ->
          (let byte0 =
             push_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit1 (Bit1 (Bit1
(Bit1 (Bit1 (Bit1 (Bit1 One))))))))))
             in
           let byte1 =
             push_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 (Bit1
    (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))
             in
           let byte2 =
             push_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit1
  (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))
             in
           let byte3 =
             push_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 One))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1
(Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))))))))))
             in
           let byte4 =
             drop_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 One))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1
    (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))))))))))))))))))
             in
           let byte5 =
             drop_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
One))))))))))))))))))))))))))))))))))))))))))))))))))
             in
           let byte6 =
             drop_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
    One))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
             in
           let byte7 =
             drop_bit_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
               (and_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 n (of_int
                     (len_bit0
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
(Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
    (Bit0 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
  (Bit1 One))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
             in
            Vlong (or_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    (or_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (or_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (or_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (or_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (or_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (or_word
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                byte0 byte1)
                              byte2)
                            byte3)
                          byte4)
                        byte5)
                      byte6)
                    byte7)));;

let rec signed_cast _B _A
  w = Word (take_bit_int (len_of _A.len0_len Type) (the_signed_int _B w));;

let rec mulhs32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint w1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint w2 ->
            (let w1s64 =
               signed_cast
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 w1
               in
             let w2s64 =
               signed_cast
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 w2
               in
             let prod64 =
               times_worda
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 w1s64 w2s64
               in
             let hi32_word64 =
               drop_bit_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))) prod64
               in
             let a =
               cast (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 hi32_word64
               in
              Vint a)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec mulhs64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong w1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong w2 ->
            (let w1s128 =
               signed_cast
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (len_bit0
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 w1
               in
             let w2s128 =
               signed_cast
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (len_bit0
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 w2
               in
             let prod128 =
               times_worda
                 (len_bit0
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 w1s128 w2s128
               in
             let hi64_word128 =
               drop_bit_word
                 (len_bit0
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
                 prod128
               in
             let a =
               cast (len_bit0
                      (len_bit0
                        (len_bit0
                          (len_bit0
                            (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 hi64_word128
               in
              Vlong a)));;

let rec mulhu32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint w1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint w2 ->
            (let prod64 =
               times_inta
                 (the_int
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   w1)
                 (the_int
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   w2)
               in
             let hi32 =
               divide_inta prod64
                 (power power_int (Pos (Bit0 One))
                   (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
               in
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     hi32))
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec mulhu64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong w1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong w2 ->
            (let prod128 =
               times_inta
                 (the_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   w1)
                 (the_int
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   w2)
               in
             let hi64 =
               divide_inta prod128
                 (power power_int (Pos (Bit0 One))
                   (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      hi64))));;

let rec of_nat_aux _A inc x1 i = match inc, x1, i with inc, Zero_nat, i -> i
                        | inc, Suc n, i -> of_nat_aux _A inc n (inc i);;

let rec of_nata _A
  n = of_nat_aux _A
        (fun i ->
          plus _A.semiring_numeral_semiring_1.numeral_semiring_numeral.semigroup_add_numeral.plus_semigroup_add
            i (one _A.semiring_numeral_semiring_1.numeral_semiring_numeral.one_numeral))
        n (zero _A.semiring_0_semiring_1.mult_zero_semiring_0.zero_mult_zero);;

let rec of_nat _A
  n = Word (take_bit_int (len_of _A.len0_len Type) (of_nata semiring_1_int n));;

let rec signex32
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint n ->
          (let i =
             signed_cast
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               n
             in
           let a =
             cast (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               (drop_bit_word
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))) i)
             in
            Vint a)
        | Vlong _ -> Vundef);;

let rec signex64
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint _ -> Vundef
        | Vlong n ->
          (let i =
             signed_cast
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (len_bit0
                 (len_bit0
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
               n
             in
           let a =
             cast (len_bit0
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               (drop_bit_word
                 (len_bit0
                   (len_bit0
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))) i)
             in
            Vlong a));;

let rec map f x1 = match f, x1 with f, [] -> []
              | f, x21 :: x22 -> f x21 :: map f x22;;

let rec divmod32s
  v1 v2 v3 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint nh ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint nl ->
            (match v3 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
              | Vint d ->
                (if equal_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      d (zero_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  then None
                  else (let dividend =
                          plus_inta
                            (times_inta
                              (the_signed_int
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                nh)
                              (power power_int (Pos (Bit0 One))
                                (nat_of_num
                                  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                            (the_int
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                              nl)
                          in
                        let divisor =
                          the_signed_int
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                            d
                          in
                        let q = sdiv0 dividend divisor in
                        let r = smod0 dividend divisor in
                         (if less_eq_int
                               (uminus_inta
                                 (power power_int (Pos (Bit0 One))
                                   (nat_of_num
                                     (Bit1 (Bit1 (Bit1 (Bit1 One)))))))
                               q &&
                               less_eq_int q
                                 (minus_inta
                                   (power power_int (Pos (Bit0 One))
                                     (nat_of_num
                                       (Bit1 (Bit1 (Bit1 (Bit1 One))))))
                                   one_inta)
                           then Some (Vint
(of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) q),
                                       Vint
 (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) r))
                           else None)))
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Vlong _ -> None);;

let rec divide_word _A
  a b = of_int _A (divide_inta (the_int _A a) (the_int _A b));;

let u32_MAX : num1 bit0 bit0 bit0 bit0 bit0 word
  = of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
      (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))))))));;

let rec divmod32u
  v1 v2 v3 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint nh ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint nl ->
            (match v3 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
              | Vint d ->
                (if not (equal_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          d (zero_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                  then (let divisor =
                          cast (len_bit0
                                 (len_bit0
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            d
                          in
                        let dividend =
                          or_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (push_bit_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (nat_of_num
                                (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
                              (cast (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                nh))
                            (cast (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              nl)
                          in
                        let quotient =
                          divide_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            dividend divisor
                          in
                        let remainder =
                          modulo_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            dividend divisor
                          in
                         (if less_eq_word
                               (len_bit0
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1))))))
                               quotient
                               (cast (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))))
                                 u32_MAX)
                           then Some (Vint
(cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
  (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) quotient),
                                       Vint
 (cast (len_bit0
         (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) remainder))
                           else None))
                  else None)
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Vlong _ -> None);;

let rec divmod64s
  v1 v2 v3 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint _ -> None
      | Vlong nh ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint _ -> None
          | Vlong nl ->
            (match v3 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
              | Vint _ -> None
              | Vlong d ->
                (if equal_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      d (zero_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                  then None
                  else (let dividend =
                          plus_inta
                            (times_inta
                              (the_signed_int
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                nh)
                              (power power_int (Pos (Bit0 One))
                                (nat_of_num
                                  (Bit0 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                            (the_int
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              nl)
                          in
                        let divisor =
                          the_signed_int
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            d
                          in
                        let q = sdiv0 dividend divisor in
                        let r = smod0 dividend divisor in
                         (if less_eq_int
                               (uminus_inta
                                 (power power_int (Pos (Bit0 One))
                                   (nat_of_num
                                     (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))
                               q &&
                               less_eq_int q
                                 (minus_inta
                                   (power power_int (Pos (Bit0 One))
                                     (nat_of_num
                                       (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One)))))))
                                   one_inta)
                           then Some (Vlong
(of_int
  (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) q),
                                       Vlong
 (of_int
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   r))
                           else None))))));;

let u64_MAX : num1 bit0 bit0 bit0 bit0 bit0 bit0 word
  = of_int
      (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
      (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1
 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))));;

let rec divmod64u
  v1 v2 v3 =
    (match v1 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
      | Vint _ -> None
      | Vlong nh ->
        (match v2 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
          | Vint _ -> None
          | Vlong nl ->
            (match v3 with Vundef -> None | Vbyte _ -> None | Vshort _ -> None
              | Vint _ -> None
              | Vlong d ->
                (if not (equal_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          d (zero_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1))))))))
                  then (let dividend =
                          or_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1)))))))
                            (push_bit_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))))
                              (nat_of_num
                                (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
                              (cast (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                                nh))
                            (cast (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))))
                              nl)
                          in
                        let quotient =
                          divide_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1)))))))
                            dividend
                            (cast (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))))
                              d)
                          in
                        let remainder =
                          modulo_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1)))))))
                            dividend
                            (cast (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))))
                              d)
                          in
                         (if less_eq_word
                               (len_bit0
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1)))))))
                               quotient
                               (cast (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                                 u64_MAX)
                           then Some (Vlong
(cast (len_bit0
        (len_bit0
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
  (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
  quotient),
                                       Vlong
 (cast (len_bit0
         (len_bit0
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
   remainder))
                           else None))
                  else None))));;

let rec longofints
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint i ->
          Vlong (signed_cast
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  i)
        | Vlong _ -> Vundef);;

let rec word_sless _A
  a b = less_int (the_signed_int _A a) (the_signed_int _A b);;

let rec negative32
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint n ->
          Vint (if word_sless
                     (len_signed
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                     (signed_cast
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                       (len_signed
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                       n)
                     (zero_word
                       (len_signed
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                 then one_worda
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                 else zero_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
        | Vlong _ -> Vundef);;

let rec negative64
  v = (match v with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
        | Vint _ -> Vundef
        | Vlong n ->
          Vlong (if word_sless
                      (len_signed
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                      (signed_cast
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (len_signed
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                        n)
                      (zero_word
                        (len_signed
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                  then one_worda
                         (len_bit0
                           (len_bit0
                             (len_bit0
                               (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  else zero_word
                         (len_bit0
                           (len_bit0
                             (len_bit0
                               (len_bit0 (len_bit0 (len_bit0 len_num1))))))));;

let rec gen_length n x1 = match n, x1 with n, x :: xs -> gen_length (Suc n) xs
                     | n, [] -> n;;

let rec equal_bool p pa = match p, pa with p, true -> p
                     | p, false -> not p
                     | true, p -> p
                     | false, p -> not p;;

let rec sub_overflowi32
  x y bin =
    (let x_sign = msb32 x in
     let y_sign = msb32 y in
     let res =
       minus_word
         (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) x y
       in
     let res_sign = msb32 res in
      (if not (equal_bool x_sign y_sign) && not (equal_bool res_sign x_sign)
        then one_worda
               (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
        else zero_word
               (len_bit0
                 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))));;

let rec sub_overflow32
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            Vint (sub_overflowi32 n1 n2
                   (zero_word
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec sub_overflowi64
  x y bin =
    (let x_msb = msb64 x in
     let y_msb = msb64 y in
     let res =
       minus_word
         (len_bit0
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
         x y
       in
     let res_msb = msb64 res in
      (if not (equal_bool x_msb y_msb) && not (equal_bool res_msb x_msb)
        then one_worda
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
        else zero_word
               (len_bit0
                 (len_bit0
                   (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))));;

let rec sub_overflow64
  v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            Vint (cast (len_bit0
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   (sub_overflowi64 n1 n2
                     (zero_word
                       (len_bit0
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))))))))));;

let rec cond_of_u8
  i = (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One)))
        then Some Cond_b
        else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (Pos (Bit1 One)))
               then Some Cond_ae
               else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 One))))
                      then Some Cond_e
                      else (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 (Bit0 One))))
                             then Some Cond_ne
                             else (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) i
(of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit1 One))))
                                    then Some Cond_be
                                    else (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) i
       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (Pos (Bit1 (Bit1 One))))
   then Some Cond_a
   else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
              (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (Pos (Bit0 (Bit1 (Bit0 One)))))
          then Some Cond_p
          else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit1 (Bit1 (Bit0 One)))))
                 then Some Cond_np
                 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit0 (Bit1 One)))))
                        then Some Cond_l
                        else (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit1 (Bit0 (Bit1 One)))))
                               then Some Cond_ge
                               else (if equal_word
  (len_bit0 (len_bit0 (len_bit0 len_num1))) i
  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
    (Pos (Bit0 (Bit1 (Bit1 One)))))
                                      then Some Cond_le
                                      else (if equal_word
         (len_bit0 (len_bit0 (len_bit0 len_num1))) i
         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (Pos (Bit1 (Bit1 (Bit1 One)))))
     then Some Cond_g else None))))))))))));;

let rec ireg_of_u8
  i = (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
        then Some RAX
        else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
               then Some RCX
               else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 One)))
                      then Some RDX
                      else (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 One)))
                             then Some RBX
                             else (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) i
(of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit0 One))))
                                    then Some RSP
                                    else (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) i
       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (Pos (Bit1 (Bit0 One))))
   then Some RBP
   else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
              (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (Pos (Bit0 (Bit1 One))))
          then Some RSI
          else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit1 (Bit1 One))))
                 then Some RDI
                 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit0 (Bit0 One)))))
                        then Some R8
                        else (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit1 (Bit0 (Bit0 One)))))
                               then Some R9
                               else (if equal_word
  (len_bit0 (len_bit0 (len_bit0 len_num1))) i
  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
    (Pos (Bit0 (Bit1 (Bit0 One)))))
                                      then Some R10
                                      else (if equal_word
         (len_bit0 (len_bit0 (len_bit0 len_num1))) i
         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (Pos (Bit1 (Bit1 (Bit0 One)))))
     then Some R11
     else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (Pos (Bit0 (Bit0 (Bit1 One)))))
            then Some R12
            else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (Pos (Bit1 (Bit0 (Bit1 One)))))
                   then Some R13
                   else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              i (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit0 (Bit1 (Bit1 One)))))
                          then Some R14
                          else (if equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))) i
                                     (of_int
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       (Pos (Bit1 (Bit1 (Bit1 One)))))
                                 then Some R15 else None))))))))))))))));;

let rec undef_regs
  x0 rs = match x0, rs with [], rs -> rs
    | r :: l, rs -> undef_regs l (fun_upd equal_preg rs r Vundef);;

let rec nextinstr sz rs = fun_upd equal_preg rs PC (add64 (rs PC) (Vlong sz));;

let rec nextinstr_nf
  sz rs = nextinstr sz (undef_regs [CR ZF; CR CF; CR PF; CR SF; CR OF] rs);;

let rec vlong_of_memory_chunk
  chunk =
    (match chunk
      with M8 ->
        Vlong (one_worda
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
      | M16 ->
        Vlong (of_int
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                (Pos (Bit0 One)))
      | M32 ->
        Vlong (of_int
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                (Pos (Bit0 (Bit0 One))))
      | M64 ->
        Vlong (of_int
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                (Pos (Bit0 (Bit0 (Bit0 One))))));;

let rec exec_pop
  sz chunk m rs rd =
    (let nsp = add64 (rs (IR RSP)) (vlong_of_memory_chunk chunk) in
      (match rs (IR RSP) with Vundef -> Stuck | Vbyte _ -> Stuck
        | Vshort _ -> Stuck | Vint _ -> Stuck
        | Vlong addr ->
          (match loadv chunk m addr with None -> Stuck
            | Some v ->
              (let rs1 = fun_upd equal_preg rs rd v in
                Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR RSP) nsp),
                       m)))));;

let rec exec_ret
  sz chunk m rs =
    (let nsp = add64 (rs (IR RSP)) (vlong_of_memory_chunk chunk) in
      (match nsp with Vundef -> Stuck | Vbyte _ -> Stuck | Vshort _ -> Stuck
        | Vint _ -> Stuck
        | Vlong addr ->
          (match loadv M64 m addr with None -> Stuck
            | Some ra ->
              (let rs1 = fun_upd equal_preg rs (IR RSP) nsp in
                Next (fun_upd equal_preg rs1 PC ra, m)))));;

let rec bitfield_extract _A
  pos width n =
    and_word _A
      (minus_word _A (power (power_word _A) (of_int _A (Pos (Bit0 One))) width)
        (one_worda _A))
      (drop_bit_word _A pos n);;

let rec not_word _A w = of_int _A (not_int (the_int _A w));;

let rec bitfield_insert _A
  pos width n p =
    (let mask =
       push_bit_word _A pos
         (minus_word _A
           (power (power_word _A) (of_int _A (Pos (Bit0 One))) width)
           (one_worda _A))
       in
      or_word _A
        (push_bit_word _A pos
          (and_word _A
            (minus_word _A
              (power (power_word _A) (of_int _A (Pos (Bit0 One))) width)
              (one_worda _A))
            p))
        (and_word _A n (not_word _A mask)));;

let rec size_list x = gen_length Zero_nat x;;

let rec u32_of_u8_list
  l = (if not (equal_nat (size_list l) (nat_of_num (Bit0 (Bit0 One)))) then None
        else Some (or_word
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (push_bit_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
                      (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (nth l (nat_of_num (Bit1 One)))))
                    (or_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (push_bit_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One)))))
                        (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (nth l (nat_of_num (Bit0 One)))))
                      (or_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (push_bit_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                          (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                            (nth l one_nat)))
                        (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (nth l Zero_nat))))));;

let rec nth_error
  l a = (if less_eq_nat (size_list l) a then None else Some (nth l a));;

let rec x64_decode_op_not_rex
  h pc l_bin =
    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
            (nat_of_num (Bit1 One)) (nat_of_num (Bit1 (Bit0 One))) h)
          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
            (Pos (Bit0 (Bit1 (Bit0 One)))))
      then (let reg2 =
              bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                Zero_nat (nat_of_num (Bit1 One)) h
              in
            let dst =
              bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (nat_of_num (Bit1 One)) one_nat reg2
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
              in
             (match ireg_of_u8 dst with None -> None
               | Some dsta -> Some (one_nat, Ppushl_r dsta)))
      else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (nat_of_num (Bit1 One)) (nat_of_num (Bit1 (Bit0 One))) h)
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 (Bit0 One)))))
             then (let reg2 =
                     bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       Zero_nat (nat_of_num (Bit1 One)) h
                     in
                   let dst =
                     bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (nat_of_num (Bit1 One)) one_nat reg2
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                     in
                    (match ireg_of_u8 dst with None -> None
                      | Some dsta -> Some (one_nat, Ppopl dsta)))
             else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 (Bit0
     (Bit1 (Bit0 (Bit1 (Bit1 One)))))))))
                    then (match nth_error l_bin (plus_nat pc one_nat)
                           with None -> None
                           | Some i1 ->
                             (match
                               nth_error l_bin
                                 (plus_nat pc (nat_of_num (Bit0 One)))
                               with None -> None
                               | Some i2 ->
                                 (match
                                   nth_error l_bin
                                     (plus_nat pc (nat_of_num (Bit1 One)))
                                   with None -> None
                                   | Some i3 ->
                                     (match
                                       nth_error l_bin
 (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                                       with None -> None
                                       | Some i4 ->
 (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
   | Some d ->
     Some (nat_of_num (Bit1 (Bit0 One)),
            Pcall_i
              (signed_cast
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                d)))))))
                    else (if equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (Pos (Bit1
(Bit0 (Bit0 (Bit1 (Bit0 (Bit1 (Bit1 One)))))))))
                           then (match nth_error l_bin (plus_nat pc one_nat)
                                  with None -> None
                                  | Some i1 ->
                                    (match
                                      nth_error l_bin
(plus_nat pc (nat_of_num (Bit0 One)))
                                      with None -> None
                                      | Some i2 ->
(match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One))) with None -> None
  | Some i3 ->
    (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
      with None -> None
      | Some i4 ->
        (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
          | Some d ->
            Some (nat_of_num (Bit1 (Bit0 One)),
                   Pjmp (signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          d)))))))
                           else (match nth_error l_bin (plus_nat pc one_nat)
                                  with None -> None
                                  | Some reg ->
                                    (let modrm =
                                       bitfield_extract
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (nat_of_num (Bit0 (Bit1 One)))
 (nat_of_num (Bit0 One)) reg
                                       in
                                     let reg1 =
                                       bitfield_extract
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (nat_of_num (Bit1 One))
 (nat_of_num (Bit1 One)) reg
                                       in
                                     let reg2 =
                                       bitfield_extract
 (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat (nat_of_num (Bit1 One)) reg
                                       in
                                     let src =
                                       bitfield_insert
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (nat_of_num (Bit1 One)) one_nat reg1
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                       in
                                     let dst =
                                       bitfield_insert
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (nat_of_num (Bit1 One)) one_nat reg2
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                       in
                                      (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) h
    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
      (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
       then (match ireg_of_u8 src with None -> None
              | Some srca ->
                (match ireg_of_u8 dst with None -> None
                  | Some dsta ->
                    Some (nat_of_num (Bit0 One), Pmovl_rr (dsta, srca))))
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
              then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                     with None -> None
                     | Some dis ->
                       (match ireg_of_u8 src with None -> None
                         | Some srca ->
                           (match ireg_of_u8 dst with None -> None
                             | Some dsta ->
                               Some (nat_of_num (Bit1 One),
                                      Pmov_mr
(Addrmode
   (Some dsta, None,
     signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
       (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
  srca, M32)))))
              else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         modrm
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit0 One)))
                     then (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit0 One)))
                            with None -> None
                            | Some d1 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit1 One)))
                                with None -> None
                                | Some d2 ->
                                  (match
                                    nth_error l_bin
                                      (plus_nat pc
(nat_of_num (Bit0 (Bit0 One))))
                                    with None -> None
                                    | Some d3 ->
                                      (match
nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One)))) with None -> None
| Some d4 ->
  (match u32_of_u8_list [d1; d2; d3; d4] with None -> None
    | Some dis ->
      (match ireg_of_u8 src with None -> None
        | Some srca ->
          (match ireg_of_u8 dst with None -> None
            | Some dsta ->
              Some (nat_of_num (Bit0 (Bit1 One)),
                     Pmov_mr
                       (Addrmode (Some dsta, None, dis), srca, M32)))))))))
                     else None)))
else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
           (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
       then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
              then (match ireg_of_u8 src with None -> None
                     | Some srca ->
                       (match ireg_of_u8 dst with None -> None
                         | Some dsta ->
                           Some (nat_of_num (Bit0 One), Paddl_rr (dsta, srca))))
              else None)
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One)))))))))
              then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         modrm
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit1 One))) &&
                         equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           reg1
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 One)))
                     then (match ireg_of_u8 dst with None -> None
                            | Some dsta ->
                              Some (nat_of_num (Bit0 One), Pnegl dsta))
                     else (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1 One))) &&
                                equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit0 (Bit0 One))))
                            then (match ireg_of_u8 dst with None -> None
                                   | Some dsta ->
                                     Some (nat_of_num (Bit0 One), Pmull_r dsta))
                            else (if equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       modrm
                                       (of_int
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
                                       equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 One))))
                                   then (match ireg_of_u8 dst with None -> None
  | Some dsta -> Some (nat_of_num (Bit0 One), Pimull_r dsta))
                                   else (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
      equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 One))))
  then (match ireg_of_u8 dst with None -> None
         | Some dsta -> Some (nat_of_num (Bit0 One), Pdivl_r dsta))
  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 One))) &&
             equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 One))))
         then (match ireg_of_u8 dst with None -> None
                | Some dsta -> Some (nat_of_num (Bit0 One), Pidivl_r dsta))
         else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 One))) &&
                    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                then (match
                       nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                       with None -> None
                       | Some i1 ->
                         (match
                           nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                           with None -> None
                           | Some i2 ->
                             (match
                               nth_error l_bin
                                 (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                               with None -> None
                               | Some i3 ->
                                 (match
                                   nth_error l_bin
                                     (plus_nat pc
                                       (nat_of_num (Bit1 (Bit0 One))))
                                   with None -> None
                                   | Some i4 ->
                                     (match ireg_of_u8 dst with None -> None
                                       | Some dsta ->
 (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
   | Some imm ->
     Some (nat_of_num (Bit0 (Bit1 One)), Ptestl_ri (dsta, imm))))))))
                else None))))))
              else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 One)))))))
                     then (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1 One)))
                            then (match ireg_of_u8 src with None -> None
                                   | Some srca ->
                                     (match ireg_of_u8 dst with None -> None
                                       | Some dsta ->
 Some (nat_of_num (Bit0 One), Psubl_rr (dsta, srca))))
                            else None)
                     else (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
                            then (if equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       modrm
                                       (of_int
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
                                   then (match ireg_of_u8 src with None -> None
  | Some srca ->
    (match ireg_of_u8 dst with None -> None
      | Some dsta -> Some (nat_of_num (Bit0 One), Pandl_rr (dsta, srca))))
                                   else None)
                            else (if equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       h (of_int
   (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 (Bit0 One)))))
                                   then (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
  then (match ireg_of_u8 src with None -> None
         | Some srca ->
           (match ireg_of_u8 dst with None -> None
             | Some dsta -> Some (nat_of_num (Bit0 One), Porl_rr (dsta, srca))))
  else None)
                                   else (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) h
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
        (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))
  then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
         then (match ireg_of_u8 src with None -> None
                | Some srca ->
                  (match ireg_of_u8 dst with None -> None
                    | Some dsta ->
                      Some (nat_of_num (Bit0 One), Pxorl_rr (dsta, srca))))
         else None)
  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One)))))))))
         then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 One))) &&
                    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit0 (Bit0 One))))
                then (match ireg_of_u8 dst with None -> None
                       | Some dsta ->
                         Some (nat_of_num (Bit0 One), Pshll_r dsta))
                else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           modrm
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 One))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             reg1
                             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (Pos (Bit1 (Bit0 One))))
                       then (match ireg_of_u8 dst with None -> None
                              | Some dsta ->
                                Some (nat_of_num (Bit0 One), Pshrl_r dsta))
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  modrm
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 One))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    reg1
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos (Bit1 (Bit1 One))))
                              then (match ireg_of_u8 dst with None -> None
                                     | Some dsta ->
                                       Some (nat_of_num (Bit0 One),
      Psarl_r dsta))
                              else None)))
         else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 (Bit0 (Bit1
 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           modrm
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 One)))
                       then (match ireg_of_u8 src with None -> None
                              | Some srca ->
                                (match ireg_of_u8 dst with None -> None
                                  | Some dsta ->
                                    Some (nat_of_num (Bit0 One),
   Ptestl_rr (dsta, srca))))
                       else None)
                else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit1 One)))))))
                       then (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  modrm
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 One)))
                              then (match ireg_of_u8 src with None -> None
                                     | Some srca ->
                                       (match ireg_of_u8 dst with None -> None
 | Some dsta -> Some (nat_of_num (Bit0 One), Pcmpl_rr (srca, dsta))))
                              else None)
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One)))))))))
                              then (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One)))
                                     then (match ireg_of_u8 dst
    with None -> None | Some dsta -> Some (nat_of_num (Bit0 One), Pcall_r dsta))
                                     else None)
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) h
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
                                     then (match
    nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One))) with None -> None
    | Some i1 ->
      (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
        with None -> None
        | Some i2 ->
          (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
            with None -> None
            | Some i3 ->
              (match
                nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                with None -> None
                | Some i4 ->
                  (match ireg_of_u8 dst with None -> None
                    | Some dsta ->
                      (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
                        | Some imm ->
                          (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1 One))) &&
                                equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                                  (zero_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))
                            then Some (nat_of_num (Bit0 (Bit1 One)),
Pmovl_ri (dsta, imm))
                            else None)))))))
                                     else (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) h
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
    then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
           with None -> None
           | Some imm ->
             (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (Pos (Bit1 One))) &&
                   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit0 (Bit0 One))))
               then (match ireg_of_u8 dst with None -> None
                      | Some dsta ->
                        Some (nat_of_num (Bit1 One), Pshll_ri (dsta, imm)))
               else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          modrm
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit1 One))) &&
                          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            reg1
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit1 (Bit0 One))))
                      then (match ireg_of_u8 dst with None -> None
                             | Some dsta ->
                               Some (nat_of_num (Bit1 One),
                                      Pshrl_ri (dsta, imm)))
                      else (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 One))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   reg1
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit1 (Bit1 One))))
                             then (match ireg_of_u8 dst with None -> None
                                    | Some dsta ->
                                      Some (nat_of_num (Bit1 One),
     Psarl_ri (dsta, imm)))
                             else (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
(of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                    then (match ireg_of_u8 dst with None -> None
   | Some dsta -> Some (nat_of_num (Bit1 One), Prorl_ri (dsta, imm)))
                                    else None)))))
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
           then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 One)))
                  then (match ireg_of_u8 dst with None -> None
                         | Some dsta ->
                           (match
                             nth_error l_bin
                               (plus_nat pc (nat_of_num (Bit0 One)))
                             with None -> None
                             | Some i1 ->
                               (match
                                 nth_error l_bin
                                   (plus_nat pc (nat_of_num (Bit1 One)))
                                 with None -> None
                                 | Some i2 ->
                                   (match
                                     nth_error l_bin
                                       (plus_nat pc
 (nat_of_num (Bit0 (Bit0 One))))
                                     with None -> None
                                     | Some i3 ->
                                       (match
 nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One)))) with None -> None
 | Some i4 ->
   (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
     | Some imm ->
       (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
             (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
         then Some (nat_of_num (Bit0 (Bit1 One)), Paddl_ri (dsta, imm))
         else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                    (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                then Some (nat_of_num (Bit0 (Bit1 One)), Porl_ri (dsta, imm))
                else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           reg1
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit0 (Bit0 One))))
                       then Some (nat_of_num (Bit0 (Bit1 One)),
                                   Pandl_ri (dsta, imm))
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 (Bit0 One))))
                              then Some (nat_of_num (Bit0 (Bit1 One)),
  Psubl_ri (dsta, imm))
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit1 One))))
                                     then Some (nat_of_num (Bit0 (Bit1 One)),
         Pxorl_ri (dsta, imm))
                                     else (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 One))))
    then Some (nat_of_num (Bit0 (Bit1 One)), Pcmpl_ri (dsta, imm))
    else None))))))))))))
                  else None)
           else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit0 (Bit0 (Bit0
   (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                  then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             modrm
                             (one_worda
                               (len_bit0 (len_bit0 (len_bit0 len_num1))))
                         then (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit0 One)))
                                with None -> None
                                | Some dis ->
                                  (match ireg_of_u8 src with None -> None
                                    | Some srca ->
                                      (match ireg_of_u8 dst with None -> None
| Some dsta ->
  Some (nat_of_num (Bit1 One),
         Pmov_mr
           (Addrmode
              (Some dsta, None,
                signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                  dis),
             srca, M8)))))
                         else None)
                  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             h (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (Pos (Bit1
(Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                         then (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    modrm
                                    (one_worda
                                      (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                then (match
                                       nth_error l_bin
 (plus_nat pc (nat_of_num (Bit0 One)))
                                       with None -> None
                                       | Some dis ->
 (match ireg_of_u8 src with None -> None
   | Some srca ->
     (match ireg_of_u8 dst with None -> None
       | Some dsta ->
         Some (nat_of_num (Bit1 One),
                Pmov_rm
                  (srca,
                    Addrmode
                      (Some dsta, None,
                        signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          dis),
                    M32)))))
                                else (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One)))
                                       then (match
      nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One))) with None -> None
      | Some d1 ->
        (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
          with None -> None
          | Some d2 ->
            (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
              with None -> None
              | Some d3 ->
                (match
                  nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                  with None -> None
                  | Some d4 ->
                    (match u32_of_u8_list [d1; d2; d3; d4] with None -> None
                      | Some dis ->
                        (match ireg_of_u8 src with None -> None
                          | Some srca ->
                            (match ireg_of_u8 dst with None -> None
                              | Some dsta ->
                                Some (nat_of_num (Bit0 (Bit1 One)),
                                       Pmov_rm
 (srca, Addrmode (Some dsta, None, dis), M32)))))))))
                                       else None))
                         else None))))))))))))))))))))));;

let rec x64_decode_op_0x81
  modrm dst reg1 reg2 w r x b pc l_bin =
    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
      then (match ireg_of_u8 dst with None -> None
             | Some dsta ->
               (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                 with None -> None
                 | Some i1 ->
                   (match
                     nth_error l_bin
                       (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                     with None -> None
                     | Some i2 ->
                       (match
                         nth_error l_bin
                           (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                         with None -> None
                         | Some i3 ->
                           (match
                             nth_error l_bin
                               (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                             with None -> None
                             | Some i4 ->
                               (match u32_of_u8_list [i1; i2; i3; i4]
                                 with None -> None
                                 | Some imm ->
                                   (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                     then (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) w
        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
        (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
           (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
    then Some (nat_of_num (Bit1 (Bit1 One)), Paddl_ri (dsta, imm)) else None)
                                     else (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
        (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
    then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
               (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
           then Some (nat_of_num (Bit1 (Bit1 One)), Porl_ri (dsta, imm))
           else None)
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit0 (Bit0 One))))
           then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                      (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                         (zero_word
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                        equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                  then Some (nat_of_num (Bit1 (Bit1 One)), Pandl_ri (dsta, imm))
                  else None)
           else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit0 One))))
                  then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             w (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                             (equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                               equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                 (zero_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         then Some (nat_of_num (Bit1 (Bit1 One)),
                                     Psubl_ri (dsta, imm))
                         else None)
                  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             reg1
                             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (Pos (Bit0 (Bit1 One))))
                         then (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                    (zero_word
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))) &&
                                    (equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       r (zero_word
   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) x
(zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                then Some (nat_of_num (Bit1 (Bit1 One)),
    Pxorl_ri (dsta, imm))
                                else None)
                         else (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    reg1
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos (Bit1 (Bit1 One))))
                                then (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))) w
   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
   (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
     equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                       then Some (nat_of_num (Bit1 (Bit1 One)),
           Pcmpq_ri (dsta, imm))
                                       else (if equal_word
          (len_bit0 (len_bit0 (len_bit0 len_num1))) w
          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
          (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
             (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
            equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
      then Some (nat_of_num (Bit1 (Bit1 One)), Pcmpl_ri (dsta, imm)) else None))
                                else None))))))))))))
      else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 One))) &&
                 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg2
                   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (Pos (Bit0 (Bit0 One))))
             then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                    with None -> None
                    | Some sib ->
                      (let rbase =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
                           (nat_of_num (Bit1 One)) sib
                         in
                       let rindex =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One)) sib
                         in
                       let scale =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit0 (Bit1 One)))
                           (nat_of_num (Bit0 One)) sib
                         in
                       let index =
                         bitfield_insert
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) one_nat rindex x
                         in
                       let base =
                         bitfield_insert
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) one_nat rbase b
                         in
                        (match
                          nth_error l_bin
                            (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                          with None -> None
                          | Some d1 ->
                            (match
                              nth_error l_bin
                                (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                              with None -> None
                              | Some d2 ->
                                (match
                                  nth_error l_bin
                                    (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                                  with None -> None
                                  | Some d3 ->
                                    (match
                                      nth_error l_bin
(plus_nat pc (nat_of_num (Bit1 (Bit1 One))))
                                      with None -> None
                                      | Some d4 ->
(match u32_of_u8_list [d1; d2; d3; d4] with None -> None
  | Some dis ->
    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
      then (match
             nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 (Bit0 One)))))
             with None -> None
             | Some i1 ->
               (match
                 nth_error l_bin
                   (plus_nat pc (nat_of_num (Bit1 (Bit0 (Bit0 One)))))
                 with None -> None
                 | Some i2 ->
                   (match
                     nth_error l_bin
                       (plus_nat pc (nat_of_num (Bit0 (Bit1 (Bit0 One)))))
                     with None -> None
                     | Some i3 ->
                       (match
                         nth_error l_bin
                           (plus_nat pc (nat_of_num (Bit1 (Bit1 (Bit0 One)))))
                         with None -> None
                         | Some i4 ->
                           (match u32_of_u8_list [i1; i2; i3; i4]
                             with None -> None
                             | Some imm ->
                               (if equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                     (one_worda
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1)))) &&
                                     equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       r (zero_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                 then (match ireg_of_u8 index with None -> None
| Some ri ->
  (match ireg_of_u8 base with None -> None
    | Some rb ->
      Some (nat_of_num (Bit0 (Bit0 (Bit1 One))),
             Paddq_mi
               (Addrmode
                  (Some rb, Some (ri, scale),
                    signed_cast
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      dis),
                 imm, M64))))
                                 else None))))))
      else None))))))))
             else None));;

let rec u16_of_u8_list
  l = (if not (equal_nat (size_list l) (nat_of_num (Bit0 One))) then None
        else Some (or_word (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                    (push_bit_word
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                      (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        (nth l one_nat)))
                    (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      (nth l Zero_nat))));;

let rec x64_decode_op_0x66
  pc l_bin =
    (match nth_error l_bin (plus_nat pc one_nat) with None -> None
      | Some h1 ->
        (if not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (nat_of_num (Bit0 (Bit0 One)))
                    (nat_of_num (Bit0 (Bit0 One))) h1)
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit0 (Bit0 One)))))
          then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                 with None -> None
                 | Some reg ->
                   (let modrm =
                      bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (nat_of_num (Bit0 (Bit1 One))) (nat_of_num (Bit0 One))
                        reg
                      in
                    let reg1 =
                      bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One)) reg
                      in
                    let reg2 =
                      bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        Zero_nat (nat_of_num (Bit1 One)) reg
                      in
                    let src =
                      bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (nat_of_num (Bit1 One)) one_nat reg1
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      in
                    let dst =
                      bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (nat_of_num (Bit1 One)) one_nat reg2
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      in
                     (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h1
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
                       then (match
                              nth_error l_bin
                                (plus_nat pc (nat_of_num (Bit1 One)))
                              with None -> None
                              | Some imm ->
                                (if equal_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      modrm
                                      (of_int
(len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
                                      equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) src
(zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                  then (match ireg_of_u8 dst with None -> None
 | Some dsta -> Some (nat_of_num (Bit0 (Bit0 One)), Prolw_ri (dsta, imm)))
                                  else None))
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) h1
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                              then (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
                                     then (match ireg_of_u8 dst
    with None -> None
    | Some dsta ->
      (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
        with None -> None
        | Some i1 ->
          (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
            with None -> None
            | Some i2 ->
              (match u16_of_u8_list [i1; i2] with None -> None
                | Some imm ->
                  (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                    then Some (nat_of_num (Bit1 (Bit0 One)),
                                Paddw_ri (dsta, imm))
                    else None)))))
                                     else None)
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) h1
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                                     then (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
        (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
    then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
           with None -> None
           | Some dis ->
             (match ireg_of_u8 src with None -> None
               | Some srca ->
                 (match ireg_of_u8 dst with None -> None
                   | Some dsta ->
                     Some (nat_of_num (Bit0 (Bit0 One)),
                            Pmov_mr
                              (Addrmode
                                 (Some dsta, None,
                                   signed_cast
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (len_bit0
                                       (len_bit0
 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                     dis),
                                srca, M16)))))
    else None)
                                     else None)))))
          else (let w =
                  bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (nat_of_num (Bit1 One)) one_nat h1
                  in
                let r =
                  bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (nat_of_num (Bit0 One)) one_nat h1
                  in
                let x =
                  bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    one_nat one_nat h1
                  in
                let b =
                  bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    Zero_nat one_nat h1
                  in
                 (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                   with None -> None
                   | Some op ->
                     (match
                       nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                       with None -> None
                       | Some reg ->
                         (let modrm =
                            bitfield_extract
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (nat_of_num (Bit0 (Bit1 One)))
                              (nat_of_num (Bit0 One)) reg
                            in
                          let reg1 =
                            bitfield_extract
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One))
                              reg
                            in
                          let reg2 =
                            bitfield_extract
                              (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
                              (nat_of_num (Bit1 One)) reg
                            in
                          let src =
                            bitfield_insert
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (nat_of_num (Bit1 One)) one_nat reg1 r
                            in
                          let dst =
                            bitfield_insert
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (nat_of_num (Bit1 One)) one_nat reg2 b
                            in
                           (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
                             then (match
                                    nth_error l_bin
                                      (plus_nat pc
(nat_of_num (Bit0 (Bit0 One))))
                                    with None -> None
                                    | Some imm ->
                                      (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) src
      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
then (match ireg_of_u8 dst with None -> None
       | Some dsta ->
         (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
               (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
           then Some (nat_of_num (Bit1 (Bit0 One)), Prolw_ri (dsta, imm))
           else None))
else None))
                             else (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) op
(of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                                    then (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
   then (match ireg_of_u8 dst with None -> None
          | Some dsta ->
            (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
              with None -> None
              | Some i1 ->
                (match
                  nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                  with None -> None
                  | Some i2 ->
                    (match u16_of_u8_list [i1; i2] with None -> None
                      | Some imm ->
                        (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              reg1
                              (zero_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                              (equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                 (zero_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                (equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                   (zero_word
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                    (zero_word
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                          then Some (nat_of_num (Bit0 (Bit1 One)),
                                      Paddw_ri (dsta, imm))
                          else None)))))
   else None)
                                    else (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) op
       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
   then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
              (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
          then (match
                 nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                 with None -> None
                 | Some dis ->
                   (match ireg_of_u8 src with None -> None
                     | Some srca ->
                       (match ireg_of_u8 dst with None -> None
                         | Some dsta ->
                           (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                 (zero_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                   (zero_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))))
                             then Some (nat_of_num (Bit1 (Bit0 One)),
 Pmov_mr
   (Addrmode
      (Some dsta, None,
        signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
     srca, M16))
                             else None))))
          else None)
   else None)))))))));;

let rec x64_decode_op_0x0f
  pc l_bin =
    (match nth_error l_bin (plus_nat pc one_nat) with None -> None
      | Some op ->
        (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (nat_of_num (Bit1 One)) (nat_of_num (Bit1 (Bit0 One))) op)
              (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (Pos (Bit1 (Bit0 (Bit0 (Bit1 One))))))
          then (let reg2 =
                  bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    Zero_nat (nat_of_num (Bit1 One)) op
                  in
                let dst =
                  bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (nat_of_num (Bit1 One)) one_nat reg2
                    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  in
                 (match ireg_of_u8 dst with None -> None
                   | Some dsta -> Some (nat_of_num (Bit0 One), Pbswapl dsta)))
          else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (nat_of_num (Bit0 (Bit0 One)))
                       (nat_of_num (Bit0 (Bit0 One))) op)
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit0 (Bit0 One))))
                 then (let flag =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
                           (nat_of_num (Bit0 (Bit0 One))) op
                         in
                        (match
                          nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                          with None -> None
                          | Some reg ->
                            (let modrm =
                               bitfield_extract
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (nat_of_num (Bit0 (Bit1 One)))
                                 (nat_of_num (Bit0 One)) reg
                               in
                             let reg1 =
                               bitfield_extract
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One))
                                 reg
                               in
                             let reg2 =
                               bitfield_extract
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 Zero_nat (nat_of_num (Bit1 One)) reg
                               in
                             let src =
                               bitfield_insert
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (nat_of_num (Bit1 One)) one_nat reg1
                                 (zero_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))
                               in
                             let dst =
                               bitfield_insert
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (nat_of_num (Bit1 One)) one_nat reg2
                                 (zero_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))
                               in
                              (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    modrm
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos (Bit1 One)))
                                then (match cond_of_u8 flag with None -> None
                                       | Some t ->
 (match ireg_of_u8 src with None -> None
   | Some srca ->
     (match ireg_of_u8 dst with None -> None
       | Some dsta -> Some (nat_of_num (Bit1 One), Pcmovl (t, srca, dsta)))))
                                else None))))
                 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (bitfield_extract
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (nat_of_num (Bit0 (Bit0 One)))
                              (nat_of_num (Bit0 (Bit0 One))) op)
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit0 (Bit0 One)))))
                        then (let flag =
                                bitfield_extract
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  Zero_nat (nat_of_num (Bit0 (Bit0 One))) op
                                in
                               (match
                                 nth_error l_bin
                                   (plus_nat pc (nat_of_num (Bit0 One)))
                                 with None -> None
                                 | Some i1 ->
                                   (match
                                     nth_error l_bin
                                       (plus_nat pc (nat_of_num (Bit1 One)))
                                     with None -> None
                                     | Some i2 ->
                                       (match
 nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One)))) with None -> None
 | Some i3 ->
   (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
     with None -> None
     | Some i4 ->
       (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
         | Some d ->
           (match cond_of_u8 flag with None -> None
             | Some t -> Some (nat_of_num (Bit0 (Bit1 One)), Pjcc (t, d)))))))))
                        else None))));;

let rec u64_of_u8_list
  l = (if not (equal_nat (size_list l) (nat_of_num (Bit0 (Bit0 (Bit0 One)))))
        then None
        else Some (or_word
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    (push_bit_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
                      (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (nth l (nat_of_num (Bit1 (Bit1 One))))))
                    (or_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (push_bit_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))
                        (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth l (nat_of_num (Bit0 (Bit1 One))))))
                      (or_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (push_bit_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
                          (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (nth l (nat_of_num (Bit1 (Bit0 One))))))
                        (or_word
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (push_bit_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
                            (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (nth l (nat_of_num (Bit0 (Bit0 One))))))
                          (or_word
                            (len_bit0
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                            (push_bit_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (nat_of_num (Bit0 (Bit0 (Bit0 (Bit1 One)))))
                              (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                (nth l (nat_of_num (Bit1 One)))))
                            (or_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                              (push_bit_word
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                (nat_of_num (Bit0 (Bit0 (Bit0 (Bit0 One)))))
                                (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  (nth l (nat_of_num (Bit0 One)))))
                              (or_word
                                (len_bit0
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 len_num1))))))
                                (push_bit_word
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  (nat_of_num (Bit0 (Bit0 (Bit0 One))))
                                  (cast (len_bit0
  (len_bit0 (len_bit0 len_num1)))
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                    (nth l one_nat)))
                                (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (len_bit0
                                    (len_bit0
                                      (len_bit0
(len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                  (nth l Zero_nat))))))))));;

let rec x64_decode
  pc l_bin =
    (match nth_error l_bin pc with None -> None
      | Some h ->
        (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
              (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 One)))))))))
          then Some (one_nat, Pnop)
          else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit1 (Bit0 (Bit0
  (Bit1 (Bit1 (Bit0 (Bit0 One)))))))))
                 then Some (one_nat, Pcdq)
                 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                            (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit1 (Bit1
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
                        then Some (one_nat, Pret)
                        else (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) h
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit0
    (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 One))))))))
                               then x64_decode_op_0x66 pc l_bin
                               else (if equal_word
  (len_bit0 (len_bit0 (len_bit0 len_num1))) h
  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
    (Pos (Bit1 (Bit1 (Bit1 One)))))
                                      then x64_decode_op_0x0f pc l_bin
                                      else (if not
         (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
             (nat_of_num (Bit0 (Bit0 One))) (nat_of_num (Bit0 (Bit0 One))) h)
           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
             (Pos (Bit0 (Bit0 One)))))
     then x64_decode_op_not_rex h pc l_bin
     else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  Zero_nat (nat_of_num (Bit0 (Bit0 One))) h)
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
            then None
            else (let w =
                    bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (nat_of_num (Bit1 One)) one_nat h
                    in
                  let r =
                    bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (nat_of_num (Bit0 One)) one_nat h
                    in
                  let x =
                    bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      one_nat one_nat h
                    in
                  let b =
                    bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      Zero_nat one_nat h
                    in
                   (match nth_error l_bin (plus_nat pc one_nat)
                     with None -> None
                     | Some op ->
                       (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             op (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1
 (Bit0 (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 One)))))))))
                         then (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                    (one_worda
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))) &&
                                    (equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       r (zero_word
   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      (equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) x
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) b
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                                then Some (nat_of_num (Bit0 One), Pcqo)
                                else None)
                         else (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (bitfield_extract
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (nat_of_num (Bit1 One))
                                      (nat_of_num (Bit1 (Bit0 One))) op)
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos (Bit0 (Bit1 (Bit0 One)))))
                                then (let reg2 =
bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
  (nat_of_num (Bit1 One)) op
in
                                      let dst =
bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (nat_of_num (Bit1 One)) one_nat reg2 b
in
                                       (match ireg_of_u8 dst with None -> None
 | Some dsta ->
   (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
         (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
             (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
     then Some (nat_of_num (Bit0 One), Ppushl_r dsta) else None)))
                                else (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
     (nat_of_num (Bit1 One)) (nat_of_num (Bit1 (Bit0 One))) op)
   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
     (Pos (Bit1 (Bit1 (Bit0 One)))))
                                       then (let reg2 =
       bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
         (nat_of_num (Bit1 One)) op
       in
     let dst =
       bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
         (nat_of_num (Bit1 One)) one_nat reg2 b
       in
      (match ireg_of_u8 dst with None -> None
        | Some dsta ->
          (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                  equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
            then Some (nat_of_num (Bit0 One), Ppopl dsta) else None)))
                                       else (if equal_word
          (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
            (nat_of_num (Bit1 One)) (nat_of_num (Bit1 (Bit0 One))) op)
          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
            (Pos (Bit1 (Bit1 (Bit1 (Bit0 One))))))
      then (let reg2 =
              bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
                Zero_nat (nat_of_num (Bit1 One)) op
              in
            let dst =
              bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (nat_of_num (Bit1 One)) one_nat reg2 b
              in
             (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
               with None -> None
               | Some i1 ->
                 (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                   with None -> None
                   | Some i2 ->
                     (match
                       nth_error l_bin
                         (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                       with None -> None
                       | Some i3 ->
                         (match
                           nth_error l_bin
                             (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                           with None -> None
                           | Some i4 ->
                             (match
                               nth_error l_bin
                                 (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                               with None -> None
                               | Some i5 ->
                                 (match
                                   nth_error l_bin
                                     (plus_nat pc
                                       (nat_of_num (Bit1 (Bit1 One))))
                                   with None -> None
                                   | Some i6 ->
                                     (match
                                       nth_error l_bin
 (plus_nat pc (nat_of_num (Bit0 (Bit0 (Bit0 One)))))
                                       with None -> None
                                       | Some i7 ->
 (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 (Bit0 One)))))
   with None -> None
   | Some i8 ->
     (match ireg_of_u8 dst with None -> None
       | Some dsta ->
         (match u64_of_u8_list [i1; i2; i3; i4; i5; i6; i7; i8]
           with None -> None
           | Some imm ->
             (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                     equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               then Some (nat_of_num (Bit0 (Bit1 (Bit0 One))),
                           Pmovq_ri (dsta, imm))
               else None))))))))))))
      else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
             then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                    with None -> None
                    | Some i1 ->
                      (match
                        nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                        with None -> None
                        | Some i2 ->
                          (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                            with None -> None
                            | Some i3 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                                with None -> None
                                | Some i4 ->
                                  (match u32_of_u8_list [i1; i2; i3; i4]
                                    with None -> None
                                    | Some imm ->
                                      (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) w
    (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
    (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
      (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
        equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) b
          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
then Some (nat_of_num (Bit0 (Bit1 One)), Ppushl_i imm) else None))))))
             else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit1 (Bit1 (Bit1 One)))))
                    then (match
                           nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                           with None -> None
                           | Some op1 ->
                             (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (bitfield_extract
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (nat_of_num (Bit1 One))
                                     (nat_of_num (Bit1 (Bit0 One))) op1)
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit1 (Bit0 (Bit0 (Bit1 One))))))
                               then (let reg2 =
                                       bitfield_extract
 (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat (nat_of_num (Bit1 One)) op1
                                       in
                                     let dst =
                                       bitfield_insert
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (nat_of_num (Bit1 One)) one_nat reg2
 b
                                       in
                                      (match ireg_of_u8 dst with None -> None
| Some dsta ->
  (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
        (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
        (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
           (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
    then Some (nat_of_num (Bit1 One), Pbswapq dsta)
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
               (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
           then Some (nat_of_num (Bit1 One), Pbswapl dsta) else None))))
                               else (if equal_word
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
    (nat_of_num (Bit0 (Bit0 One))) (nat_of_num (Bit0 (Bit0 One))) op1)
  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit0 One))))
                                      then (let flag =
      bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
        (nat_of_num (Bit0 (Bit0 One))) op1
      in
     (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
       with None -> None
       | Some reg ->
         (let modrm =
            bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (nat_of_num (Bit0 (Bit1 One))) (nat_of_num (Bit0 One)) reg
            in
          let reg1 =
            bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One)) reg
            in
          let reg2 =
            bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
              (nat_of_num (Bit1 One)) reg
            in
          let src =
            bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (nat_of_num (Bit1 One)) one_nat reg1 r
            in
          let dst =
            bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (nat_of_num (Bit1 One)) one_nat reg2 b
            in
           (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
             then (match cond_of_u8 flag with None -> None
                    | Some t ->
                      (match ireg_of_u8 src with None -> None
                        | Some srca ->
                          (match ireg_of_u8 dst with None -> None
                            | Some dsta ->
                              (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                    (zero_word
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))) &&
                                    equal_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      x (zero_word
  (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                then Some (nat_of_num (Bit0 (Bit0 One)),
    Pcmovl (t, srca, dsta))
                                else (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))) w
   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                       then Some (nat_of_num (Bit0 (Bit0 One)),
           Pcmovq (t, srca, dsta))
                                       else None)))))
             else None))))
                                      else None)))
                    else (match
                           nth_error l_bin (plus_nat pc (nat_of_num (Bit0 One)))
                           with None -> None
                           | Some reg ->
                             (let modrm =
                                bitfield_extract
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (nat_of_num (Bit0 (Bit1 One)))
                                  (nat_of_num (Bit0 One)) reg
                                in
                              let reg1 =
                                bitfield_extract
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (nat_of_num (Bit1 One))
                                  (nat_of_num (Bit1 One)) reg
                                in
                              let reg2 =
                                bitfield_extract
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  Zero_nat (nat_of_num (Bit1 One)) reg
                                in
                              let src =
                                bitfield_insert
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (nat_of_num (Bit1 One)) one_nat reg1 r
                                in
                              let dst =
                                bitfield_insert
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (nat_of_num (Bit1 One)) one_nat reg2 b
                                in
                               (if equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     op (of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                                 then (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
then (match ireg_of_u8 src with None -> None
       | Some srca ->
         (match ireg_of_u8 dst with None -> None
           | Some dsta ->
             (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
               then Some (nat_of_num (Bit1 One), Pmovq_rr (dsta, srca))
               else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                          (zero_word
                            (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      then Some (nat_of_num (Bit1 One), Pmovl_rr (dsta, srca))
                      else None))))
else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
           (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
       then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
              with None -> None
              | Some dis ->
                (match ireg_of_u8 src with None -> None
                  | Some srca ->
                    (match ireg_of_u8 dst with None -> None
                      | Some dsta ->
                        (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              w (one_worda
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                              equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          then Some (nat_of_num (Bit0 (Bit0 One)),
                                      Pmov_mr
(Addrmode
   (Some dsta, None,
     signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
       (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
  srca, M64))
                          else (if equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                     (zero_word
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1)))) &&
                                     equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       x (zero_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                 then Some (nat_of_num (Bit0 (Bit0 One)),
     Pmov_mr
       (Addrmode
          (Some dsta, None,
            signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              dis),
         srca, M32))
                                 else None)))))
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit0 One)))
              then (if not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             reg2
                             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (Pos (Bit0 (Bit0 One)))))
                     then (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 One)))
                            with None -> None
                            | Some d1 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                                with None -> None
                                | Some d2 ->
                                  (match
                                    nth_error l_bin
                                      (plus_nat pc
(nat_of_num (Bit1 (Bit0 One))))
                                    with None -> None
                                    | Some d3 ->
                                      (match
nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit1 One)))) with None -> None
| Some d4 ->
  (match u32_of_u8_list [d1; d2; d3; d4] with None -> None
    | Some dis ->
      (match ireg_of_u8 src with None -> None
        | Some srca ->
          (match ireg_of_u8 dst with None -> None
            | Some rb ->
              Some (nat_of_num (Bit1 (Bit1 One)),
                     Pmov_mr
                       (Addrmode (Some rb, None, dis), srca,
                         (if equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                               (one_worda
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                           then M64 else M32))))))))))
                     else (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 One)))
                            with None -> None
                            | Some sib ->
                              (let rbase =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   Zero_nat (nat_of_num (Bit1 One)) sib
                                 in
                               let rindex =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One))
                                   (nat_of_num (Bit1 One)) sib
                                 in
                               let scale =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit0 (Bit1 One)))
                                   (nat_of_num (Bit0 One)) sib
                                 in
                               let index =
                                 bitfield_insert
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One)) one_nat rindex x
                                 in
                               let base =
                                 bitfield_insert
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One)) one_nat rbase b
                                 in
                                (match
                                  nth_error l_bin
                                    (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                                  with None -> None
                                  | Some d1 ->
                                    (match
                                      nth_error l_bin
(plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                                      with None -> None
                                      | Some d2 ->
(match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
  with None -> None
  | Some d3 ->
    (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit1 One))))
      with None -> None
      | Some d4 ->
        (match u32_of_u8_list [d1; d2; d3; d4] with None -> None
          | Some dis ->
            (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
              then (match ireg_of_u8 src with None -> None
                     | Some srca ->
                       (match ireg_of_u8 index with None -> None
                         | Some ri ->
                           (match ireg_of_u8 base with None -> None
                             | Some rb ->
                               Some (nat_of_num (Bit0 (Bit0 (Bit0 One))),
                                      Pmov_mr
(Addrmode
   (Some rb, Some (ri, scale),
     signed_cast (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
       (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
  srca, M64)))))
              else None)))))))))
              else None)))
                                 else (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) op
    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
      (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
       then (match ireg_of_u8 src with None -> None
              | Some srca ->
                (match ireg_of_u8 dst with None -> None
                  | Some dsta ->
                    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                          (one_worda
                            (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))
                      then Some (nat_of_num (Bit1 One), Pxchgq_rr (dsta, srca))
                      else None)))
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit0 One)))
              then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg2
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit0 (Bit0 One))))
                     then (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 One)))
                            with None -> None
                            | Some sib ->
                              (let rbase =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   Zero_nat (nat_of_num (Bit1 One)) sib
                                 in
                               let rindex =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One))
                                   (nat_of_num (Bit1 One)) sib
                                 in
                               let scale =
                                 bitfield_extract
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit0 (Bit1 One)))
                                   (nat_of_num (Bit0 One)) sib
                                 in
                               let index =
                                 bitfield_insert
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One)) one_nat rindex x
                                 in
                               let base =
                                 bitfield_insert
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (nat_of_num (Bit1 One)) one_nat rbase b
                                 in
                                (match
                                  nth_error l_bin
                                    (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                                  with None -> None
                                  | Some d1 ->
                                    (match
                                      nth_error l_bin
(plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                                      with None -> None
                                      | Some d2 ->
(match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
  with None -> None
  | Some d3 ->
    (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit1 One))))
      with None -> None
      | Some d4 ->
        (match u32_of_u8_list [d1; d2; d3; d4] with None -> None
          | Some dis ->
            (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
              then (match ireg_of_u8 src with None -> None
                     | Some srca ->
                       (match ireg_of_u8 index with None -> None
                         | Some ri ->
                           (match ireg_of_u8 base with None -> None
                             | Some rb ->
                               Some (nat_of_num (Bit0 (Bit0 (Bit0 One))),
                                      Pxchgq_rm
(srca,
  Addrmode
    (Some rb, Some (ri, scale),
      signed_cast
        (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
        (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
  M64)))))
              else None))))))))
                     else None)
              else None))
else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
             (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
       then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
              then (match ireg_of_u8 src with None -> None
                     | Some srca ->
                       (match ireg_of_u8 dst with None -> None
                         | Some dsta ->
                           (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                 (one_worda
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                   (zero_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))))
                             then Some (nat_of_num (Bit1 One),
 Pmovsl_rr (srca, dsta))
                             else None)))
              else None)
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
              then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         modrm
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit1 One)))
                     then (match ireg_of_u8 src with None -> None
                            | Some srca ->
                              (match ireg_of_u8 dst with None -> None
                                | Some dsta ->
                                  (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) w
(one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                    then Some (nat_of_num (Bit1 One),
        Paddq_rr (dsta, srca))
                                    else (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) w
       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
   then Some (nat_of_num (Bit1 One), Paddl_rr (dsta, srca)) else None))))
                     else None)
              else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 One)))))))
                     then (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1 One)))
                            then (match ireg_of_u8 src with None -> None
                                   | Some srca ->
                                     (match ireg_of_u8 dst with None -> None
                                       | Some dsta ->
 (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
       (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
   then Some (nat_of_num (Bit1 One), Psubq_rr (dsta, srca))
   else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
              equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
          then Some (nat_of_num (Bit1 One), Psubl_rr (dsta, srca)) else None))))
                            else None)
                     else (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                                (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit1
 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One)))))))))
                            then (if equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       modrm
                                       (of_int
 (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
                                       equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
                                   then (match ireg_of_u8 dst with None -> None
  | Some dsta ->
    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
          (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
             (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
            equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
      then Some (nat_of_num (Bit1 One), Pnegq dsta)
      else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                 (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
             then Some (nat_of_num (Bit1 One), Pnegl dsta) else None)))
                                   else (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
      equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit0 One))))
  then (match ireg_of_u8 dst with None -> None
         | Some dsta ->
           (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                 (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                 (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
             then Some (nat_of_num (Bit1 One), Pmulq_r dsta)
             else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                        (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                           (zero_word
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    then Some (nat_of_num (Bit1 One), Pmull_r dsta) else None)))
  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 One))) &&
             equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 One))))
         then (match ireg_of_u8 dst with None -> None
                | Some dsta ->
                  (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                        (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                        (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                           (zero_word
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                          equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    then Some (nat_of_num (Bit1 One), Pimulq_r dsta)
                    else (if equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                               (equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                  (zero_word
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1)))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                   (zero_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                           then Some (nat_of_num (Bit1 One), Pimull_r dsta)
                           else None)))
         else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 One))) &&
                    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit0 (Bit1 One))))
                then (match ireg_of_u8 dst with None -> None
                       | Some dsta ->
                         (if equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                               (one_worda
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                               (equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                  (zero_word
                                    (len_bit0
                                      (len_bit0 (len_bit0 len_num1)))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                   (zero_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                           then Some (nat_of_num (Bit1 One), Pdivq_r dsta)
                           else (if equal_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      w (zero_word
  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      (equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) r
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                  then Some (nat_of_num (Bit1 One),
      Pdivl_r dsta)
                                  else None)))
                else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           modrm
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 One))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             reg1
                             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (Pos (Bit1 (Bit1 One))))
                       then (match ireg_of_u8 dst with None -> None
                              | Some dsta ->
                                (if equal_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      w (one_worda
  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      (equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) r
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                  then Some (nat_of_num (Bit1 One),
      Pidivq_r dsta)
                                  else (if equal_word
     (len_bit0 (len_bit0 (len_bit0 len_num1))) w
     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
     (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
 then Some (nat_of_num (Bit1 One), Pidivl_r dsta) else None)))
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  modrm
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 One))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    reg1
                                    (zero_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1))))
                              then (match
                                     nth_error l_bin
                                       (plus_nat pc (nat_of_num (Bit1 One)))
                                     with None -> None
                                     | Some i1 ->
                                       (match
 nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit0 One)))) with None -> None
 | Some i2 ->
   (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
     with None -> None
     | Some i3 ->
       (match nth_error l_bin (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
         with None -> None
         | Some i4 ->
           (match ireg_of_u8 dst with None -> None
             | Some dsta ->
               (match u32_of_u8_list [i1; i2; i3; i4] with None -> None
                 | Some imm ->
                   (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                         (one_worda
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                         (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             x (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     then Some (nat_of_num (Bit1 (Bit1 One)),
                                 Ptestq_ri (dsta, imm))
                     else (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                (equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                   (zero_word
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                    (zero_word
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))
                            then Some (nat_of_num (Bit1 (Bit1 One)),
Ptestl_ri (dsta, imm))
                            else None))))))))
                              else None))))))
                            else (if equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       op (of_int
    (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 (Bit0 One)))))
                                   then (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
  then (match ireg_of_u8 src with None -> None
         | Some srca ->
           (match ireg_of_u8 dst with None -> None
             | Some dsta ->
               (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                     (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                     equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 then Some (nat_of_num (Bit1 One), Porq_rr (dsta, srca))
                 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                            equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              x (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        then Some (nat_of_num (Bit1 One), Porl_rr (dsta, srca))
                        else None))))
  else None)
                                   else (if equal_word
      (len_bit0 (len_bit0 (len_bit0 len_num1))) op
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
        (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
  then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
         then (match ireg_of_u8 src with None -> None
                | Some srca ->
                  (match ireg_of_u8 dst with None -> None
                    | Some dsta ->
                      (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                            (one_worda
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                            equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              x (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        then Some (nat_of_num (Bit1 One), Pandq_rr (dsta, srca))
                        else (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                   (zero_word
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))) &&
                                   equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                     (zero_word
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))
                               then Some (nat_of_num (Bit1 One),
   Pandl_rr (dsta, srca))
                               else None))))
         else None)
  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))
         then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 One)))
                then (match ireg_of_u8 src with None -> None
                       | Some srca ->
                         (match ireg_of_u8 dst with None -> None
                           | Some dsta ->
                             (if equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                   (one_worda
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))) &&
                                   equal_word
                                     (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                     (zero_word
                                       (len_bit0
 (len_bit0 (len_bit0 len_num1))))
                               then Some (nat_of_num (Bit1 One),
   Pxorq_rr (dsta, srca))
                               else (if equal_word
  (len_bit0 (len_bit0 (len_bit0 len_num1))) w
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
  equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                      then Some (nat_of_num (Bit1 One),
          Pxorl_rr (dsta, srca))
                                      else None))))
                else None)
         else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit1 (Bit1 (Bit0
 (Bit0 (Bit1 (Bit0 (Bit1 One)))))))))
                then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           modrm
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 One))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             reg1
                             (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (Pos (Bit0 (Bit0 One))))
                       then (match ireg_of_u8 dst with None -> None
                              | Some dsta ->
                                (if equal_word
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      w (one_worda
  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      (equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) x
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                  then Some (nat_of_num (Bit1 One),
      Pshlq_r dsta)
                                  else (if equal_word
     (len_bit0 (len_bit0 (len_bit0 len_num1))) w
     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
     (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
 then Some (nat_of_num (Bit1 One), Pshll_r dsta) else None)))
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  modrm
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 One))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    reg1
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos (Bit1 (Bit0 One))))
                              then (match ireg_of_u8 dst with None -> None
                                     | Some dsta ->
                                       (if equal_word
     (len_bit0 (len_bit0 (len_bit0 len_num1))) w
     (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
     (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
 then Some (nat_of_num (Bit1 One), Pshrq_r dsta)
 else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
            (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
              equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
        then Some (nat_of_num (Bit1 One), Pshrl_r dsta) else None)))
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
 equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit1 One))))
                                     then (match ireg_of_u8 dst
    with None -> None
    | Some dsta ->
      (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
            (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
            (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
              equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
        then Some (nat_of_num (Bit1 One), Psarq_r dsta)
        else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                     equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               then Some (nat_of_num (Bit1 One), Psarl_r dsta) else None)))
                                     else None)))
                else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                           (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             (Pos (Bit1 (Bit0
  (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                       then (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  modrm
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1 One)))
                              then (match ireg_of_u8 src with None -> None
                                     | Some srca ->
                                       (match ireg_of_u8 dst with None -> None
 | Some dsta ->
   (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
         (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
         equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
           (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
     then Some (nat_of_num (Bit1 One), Ptestq_rr (dsta, srca))
     else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
            then Some (nat_of_num (Bit1 One), Ptestl_rr (dsta, srca))
            else None))))
                              else None)
                       else (if equal_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                                  (of_int
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    (Pos (Bit1
   (Bit0 (Bit0 (Bit1 (Bit1 One)))))))
                              then (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
                                     then (match ireg_of_u8 src
    with None -> None
    | Some srca ->
      (match ireg_of_u8 dst with None -> None
        | Some dsta ->
          (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
            then Some (nat_of_num (Bit1 One), Pcmpq_rr (srca, dsta))
            else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                         (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                   then Some (nat_of_num (Bit1 One), Pcmpl_rr (srca, dsta))
                   else None))))
                                     else None)
                              else (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) op
 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One)))))))))
                                     then (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
        equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One)))
    then (match ireg_of_u8 dst with None -> None
           | Some dsta ->
             (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                   (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                   (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                     equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
               then Some (nat_of_num (Bit1 One), Pcall_r dsta) else None))
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit0 One))) &&
               equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg2
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
           then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                  with None -> None
                  | Some sib ->
                    (let rbase =
                       bitfield_extract
                         (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
                         (nat_of_num (Bit1 One)) sib
                       in
                     let rindex =
                       bitfield_extract
                         (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One)) sib
                       in
                     let scale =
                       bitfield_extract
                         (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (nat_of_num (Bit0 (Bit1 One))) (nat_of_num (Bit0 One))
                         sib
                       in
                     let index =
                       bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (nat_of_num (Bit1 One)) one_nat rindex x
                       in
                     let base =
                       bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (nat_of_num (Bit1 One)) one_nat rbase b
                       in
                      (match
                        nth_error l_bin
                          (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                        with None -> None
                        | Some d1 ->
                          (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                            with None -> None
                            | Some d2 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                                with None -> None
                                | Some d3 ->
                                  (match
                                    nth_error l_bin
                                      (plus_nat pc
(nat_of_num (Bit1 (Bit1 One))))
                                    with None -> None
                                    | Some d4 ->
                                      (match u32_of_u8_list [d1; d2; d3; d4]
with None -> None
| Some dis ->
  (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 One))))
    then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
               (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
               equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
           then (match ireg_of_u8 index with None -> None
                  | Some ri ->
                    (match ireg_of_u8 base with None -> None
                      | Some rb ->
                        Some (nat_of_num (Bit0 (Bit0 (Bit0 One))),
                               Ppushq_m
                                 (Addrmode
                                    (Some rb, Some (ri, scale),
                                      signed_cast
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
(len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
                                   M64))))
           else None)
    else None))))))))
           else None))
                                     else (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) op
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
    then (let n =
            (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
              then one_nat
              else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         modrm
                         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (Pos (Bit0 One)))
                     then nat_of_num (Bit0 (Bit0 One)) else Zero_nat))
            in
           (match
             nth_error l_bin (plus_nat (plus_nat pc (nat_of_num (Bit1 One))) n)
             with None -> None
             | Some i1 ->
               (match
                 nth_error l_bin
                   (plus_nat (plus_nat pc (nat_of_num (Bit0 (Bit0 One)))) n)
                 with None -> None
                 | Some i2 ->
                   (match
                     nth_error l_bin
                       (plus_nat (plus_nat pc (nat_of_num (Bit1 (Bit0 One)))) n)
                     with None -> None
                     | Some i3 ->
                       (match
                         nth_error l_bin
                           (plus_nat
                             (plus_nat pc (nat_of_num (Bit0 (Bit1 One)))) n)
                         with None -> None
                         | Some i4 ->
                           (match ireg_of_u8 dst with None -> None
                             | Some dsta ->
                               (match u32_of_u8_list [i1; i2; i3; i4]
                                 with None -> None
                                 | Some imm ->
                                   (if equal_word
 (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
 (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
    (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                     then (if equal_word
        (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One)))
    then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
           then Some (nat_of_num (Bit1 (Bit1 One)), Pmovl_ri (dsta, imm))
           else None)
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
               (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
           then (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                      (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  then (match
                         nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                         with None -> None
                         | Some dis ->
                           Some (nat_of_num (Bit0 (Bit0 (Bit0 One))),
                                  Pmov_mi
                                    (Addrmode
                                       (Some dsta, None,
 signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))) dis),
                                      imm, M64)))
                  else None)
           else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit0 One)))
                  then (match
                         nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                         with None -> None
                         | Some d1 ->
                           (match
                             nth_error l_bin
                               (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                             with None -> None
                             | Some d2 ->
                               (match
                                 nth_error l_bin
                                   (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                                 with None -> None
                                 | Some d3 ->
                                   (match
                                     nth_error l_bin
                                       (plus_nat pc
 (nat_of_num (Bit0 (Bit1 One))))
                                     with None -> None
                                     | Some d4 ->
                                       (match u32_of_u8_list [d1; d2; d3; d4]
 with None -> None
 | Some dis ->
   (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
         (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
     then Some (nat_of_num (Bit1 (Bit1 (Bit0 One))),
                 Pmov_mi (Addrmode (Some dsta, None, dis), imm, M64))
     else None))))))
                  else None)))
                                     else None))))))))
    else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
           then x64_decode_op_0x81 modrm dst reg1 reg2 w r x b pc l_bin
           else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit1 One)))))))))
                  then (match
                         nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                         with None -> None
                         | Some imm ->
                           (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 One))) &&
                                 equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   reg1
                                   (of_int
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                     (Pos (Bit0 (Bit0 One))))
                             then (match ireg_of_u8 dst with None -> None
                                    | Some dsta ->
                                      (if equal_word
    (len_bit0 (len_bit0 (len_bit0 len_num1))) w
    (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
    (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
       (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
      equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
then Some (nat_of_num (Bit0 (Bit0 One)), Pshlq_ri (dsta, imm))
else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
           (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
           (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
             equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
       then Some (nat_of_num (Bit0 (Bit0 One)), Pshll_ri (dsta, imm))
       else None)))
                             else (if equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
(of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 One))))
                                    then (match ireg_of_u8 dst with None -> None
   | Some dsta ->
     (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
           (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
           (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
             equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
               (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
       then Some (nat_of_num (Bit0 (Bit0 One)), Pshrq_ri (dsta, imm))
       else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                  (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                  (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              then Some (nat_of_num (Bit0 (Bit0 One)), Pshrl_ri (dsta, imm))
              else None)))
                                    else (if equal_word
       (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
       (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))) &&
       equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
         (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (Pos (Bit1 (Bit1 One))))
   then (match ireg_of_u8 dst with None -> None
          | Some dsta ->
            (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                  (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                  (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                    equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                      (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              then Some (nat_of_num (Bit0 (Bit0 One)), Psarq_ri (dsta, imm))
              else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                         (zero_word
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                         (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             r (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     then Some (nat_of_num (Bit0 (Bit0 One)),
                                 Psarl_ri (dsta, imm))
                     else None)))
   else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
              (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                (Pos (Bit1 One))) &&
              equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg1
                (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
          then (match ireg_of_u8 dst with None -> None
                 | Some dsta ->
                   (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                         (one_worda
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                         (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                            (zero_word
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                           equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             r (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     then Some (nat_of_num (Bit0 (Bit0 One)),
                                 Prorq_ri (dsta, imm))
                     else (if equal_word
                                (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                (zero_word
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                (equal_word
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                                   (zero_word
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))) &&
                                  equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) r
                                    (zero_word
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))))
                            then Some (nat_of_num (Bit0 (Bit0 One)),
Prorl_ri (dsta, imm))
                            else None)))
          else None)))))
                  else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             op (of_int
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                  (Pos (Bit0
 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                         then (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    modrm
                                    (one_worda
                                      (len_bit0
(len_bit0 (len_bit0 len_num1)))) &&
                                    (equal_word
                                       (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                       x (zero_word
   (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                                      equal_word
(len_bit0 (len_bit0 (len_bit0 len_num1))) w
(zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                then (match
                                       nth_error l_bin
 (plus_nat pc (nat_of_num (Bit1 One)))
                                       with None -> None
                                       | Some dis ->
 (match ireg_of_u8 src with None -> None
   | Some srca ->
     (match ireg_of_u8 dst with None -> None
       | Some dsta ->
         Some (nat_of_num (Bit0 (Bit0 One)),
                Pmov_mr
                  (Addrmode
                     (Some dsta, None,
                       signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         dis),
                    srca, M8)))))
                                else None)
                         else (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1))) op
                                    (of_int
                                      (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                      (Pos
(Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                                then (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
   (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
   equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
     (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                                       then (match
      nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One))) with None -> None
      | Some dis ->
        (match ireg_of_u8 src with None -> None
          | Some srca ->
            (match ireg_of_u8 dst with None -> None
              | Some dsta ->
                Some (nat_of_num (Bit0 (Bit0 One)),
                       Pmov_rm
                         (srca,
                           Addrmode
                             (Some dsta, None,
                               signed_cast
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                                 dis),
                           (if equal_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))) w
                                 (one_worda
                                   (len_bit0 (len_bit0 (len_bit0 len_num1))))
                             then M64 else M32))))))
                                       else (if equal_word
          (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One)))
      then (if not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) reg2
                     (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                       (Pos (Bit0 (Bit0 One)))))
             then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                    with None -> None
                    | Some d1 ->
                      (match
                        nth_error l_bin
                          (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                        with None -> None
                        | Some d2 ->
                          (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                            with None -> None
                            | Some d3 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                                with None -> None
                                | Some d4 ->
                                  (match u32_of_u8_list [d1; d2; d3; d4]
                                    with None -> None
                                    | Some dis ->
                                      (match ireg_of_u8 src with None -> None
| Some srca ->
  (match ireg_of_u8 dst with None -> None
    | Some dsta ->
      (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
            (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
        then Some (nat_of_num (Bit1 (Bit1 One)),
                    Pmov_rm
                      (srca, Addrmode (Some dsta, None, dis),
                        (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              w (one_worda
                                  (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          then M64 else M32)))
        else None))))))))
             else (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                    with None -> None
                    | Some sib ->
                      (let rbase =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
                           (nat_of_num (Bit1 One)) sib
                         in
                       let rindex =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One)) sib
                         in
                       let scale =
                         bitfield_extract
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit0 (Bit1 One)))
                           (nat_of_num (Bit0 One)) sib
                         in
                       let index =
                         bitfield_insert
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) one_nat rindex x
                         in
                       let base =
                         bitfield_insert
                           (len_bit0 (len_bit0 (len_bit0 len_num1)))
                           (nat_of_num (Bit1 One)) one_nat rbase b
                         in
                        (match
                          nth_error l_bin
                            (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                          with None -> None
                          | Some d1 ->
                            (match
                              nth_error l_bin
                                (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                              with None -> None
                              | Some d2 ->
                                (match
                                  nth_error l_bin
                                    (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                                  with None -> None
                                  | Some d3 ->
                                    (match
                                      nth_error l_bin
(plus_nat pc (nat_of_num (Bit1 (Bit1 One))))
                                      with None -> None
                                      | Some d4 ->
(match u32_of_u8_list [d1; d2; d3; d4] with None -> None
  | Some dis ->
    (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
      then (match ireg_of_u8 src with None -> None
             | Some srca ->
               (match ireg_of_u8 index with None -> None
                 | Some ri ->
                   (match ireg_of_u8 base with None -> None
                     | Some rb ->
                       Some (nat_of_num (Bit0 (Bit0 (Bit0 One))),
                              Pmov_rm
                                (srca,
                                  Addrmode (Some rb, Some (ri, scale), dis),
                                  M64)))))
      else None)))))))))
      else None))
                                else (if equal_word
   (len_bit0 (len_bit0 (len_bit0 len_num1))) op
   (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
     (Pos (Bit1 (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 One)))))))))
                                       then (if equal_word
          (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
      then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
             with None -> None
             | Some dis ->
               (match ireg_of_u8 src with None -> None
                 | Some srca ->
                   (match ireg_of_u8 dst with None -> None
                     | Some dsta ->
                       (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             w (one_worda
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
                             equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1))) x
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                         then Some (nat_of_num (Bit0 (Bit0 One)),
                                     Pleaq (srca,
     Addrmode
       (Some dsta, None,
         signed_cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
           (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
           dis)))
                         else None))))
      else (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) modrm
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 One)))
             then (match nth_error l_bin (plus_nat pc (nat_of_num (Bit1 One)))
                    with None -> None
                    | Some d1 ->
                      (match
                        nth_error l_bin
                          (plus_nat pc (nat_of_num (Bit0 (Bit0 One))))
                        with None -> None
                        | Some d2 ->
                          (match
                            nth_error l_bin
                              (plus_nat pc (nat_of_num (Bit1 (Bit0 One))))
                            with None -> None
                            | Some d3 ->
                              (match
                                nth_error l_bin
                                  (plus_nat pc (nat_of_num (Bit0 (Bit1 One))))
                                with None -> None
                                | Some d4 ->
                                  (match u32_of_u8_list [d1; d2; d3; d4]
                                    with None -> None
                                    | Some dis ->
                                      (match ireg_of_u8 src with None -> None
| Some srca ->
  (match ireg_of_u8 dst with None -> None
    | Some dsta ->
      (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) w
            (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))) &&
            equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) x
              (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
        then Some (nat_of_num (Bit1 (Bit1 One)),
                    Pleaq (srca, Addrmode (Some dsta, None, dis)))
        else None))))))))
             else None))
                                       else None)))))))))))))))))))))))))))))))))))));;

let rec eval_addrmode64_val
  a rs =
    (let Addrmode (base, ofs, const) = a in
      add64 (match base
              with None ->
                Vlong (zero_word
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
              | Some r -> rs (IR r))
        (add64
          (match ofs
            with None ->
              Vlong (zero_word
                      (len_bit0
                        (len_bit0
                          (len_bit0
                            (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
            | Some (r, sc) ->
              shl64 (rs (IR r))
                (Vbyte
                  (cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (len_bit0 (len_bit0 (len_bit0 len_num1))) sc)))
          (Vlong
            (signed_cast
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              const))));;

let rec eval_addrmode64
  a rs =
    (match eval_addrmode64_val a rs with Vundef -> None | Vbyte _ -> None
      | Vshort _ -> None | Vint _ -> None | Vlong aa -> Some aa);;

let rec eval_testcond
  c rs =
    (match c
      with Cond_e ->
        (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (one_worda
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None)
      | Cond_ne ->
        (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (zero_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None)
      | Cond_b ->
        (match rs (CR CF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (one_worda
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None)
      | Cond_be ->
        (match rs (CR CF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint ca ->
            (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint z ->
                Some (equal_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        ca (one_worda
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) ||
                       equal_word
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         z (one_worda
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_ae ->
        (match rs (CR CF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (zero_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None)
      | Cond_a ->
        (match rs (CR CF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint ca ->
            (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint z ->
                Some (equal_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        ca (zero_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))) &&
                       equal_word
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         z (zero_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_l ->
        (match rs (CR OF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            (match rs (CR SF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint s ->
                Some (equal_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                       (xor_word
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         n s)
                       (one_worda
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_le ->
        (match rs (CR OF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            (match rs (CR SF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint s ->
                (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
                  | Vshort _ -> None
                  | Vint z ->
                    Some (equal_word
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                            (xor_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                              n s)
                            (one_worda
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 len_num1)))))) ||
                           equal_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                             z (one_worda
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))))))
                  | Vlong _ -> None)
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_ge ->
        (match rs (CR OF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            (match rs (CR SF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint s ->
                Some (equal_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                       (xor_word
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         n s)
                       (zero_word
                         (len_bit0
                           (len_bit0
                             (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_g ->
        (match rs (CR OF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            (match rs (CR SF) with Vundef -> None | Vbyte _ -> None
              | Vshort _ -> None
              | Vint s ->
                (match rs (CR ZF) with Vundef -> None | Vbyte _ -> None
                  | Vshort _ -> None
                  | Vint z ->
                    Some (equal_word
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                            (xor_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                              n s)
                            (zero_word
                              (len_bit0
                                (len_bit0
                                  (len_bit0
                                    (len_bit0 (len_bit0 len_num1)))))) &&
                           equal_word
                             (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                             z (zero_word
                                 (len_bit0
                                   (len_bit0
                                     (len_bit0
                                       (len_bit0 (len_bit0 len_num1)))))))
                  | Vlong _ -> None)
              | Vlong _ -> None)
          | Vlong _ -> None)
      | Cond_p ->
        (match rs (CR PF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (one_worda
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None)
      | Cond_np ->
        (match rs (CR PF) with Vundef -> None | Vbyte _ -> None
          | Vshort _ -> None
          | Vint n ->
            Some (equal_word
                   (len_bit0
                     (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                   n (zero_word
                       (len_bit0
                         (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
          | Vlong _ -> None));;

let rec compare_longs
  x y rs =
    fun_upd equal_preg
      (fun_upd equal_preg
        (fun_upd equal_preg
          (fun_upd equal_preg (fun_upd equal_preg rs (CR ZF) (cmplu Ceq x y))
            (CR CF) (cmplu Clt x y))
          (CR SF) (negative64 (sub64 x y)))
        (CR OF) (sub_overflow64 x y))
      (CR PF) Vundef;;

let rec compare_ints
  x y rs =
    (let r = sub32 x y in
      fun_upd equal_preg
        (fun_upd equal_preg
          (fun_upd equal_preg
            (fun_upd equal_preg
              (fun_upd equal_preg rs (CR ZF)
                (cmpu Ceq r
                  (Vint (zero_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))))))
              (CR CF) (cmpu Clt x y))
            (CR SF) (negative32 r))
          (CR OF) (sub_overflow32 x y))
        (CR PF) Vundef);;

let rec exec_store
  sz chunk m a rs r1 destroyed =
    (match eval_addrmode64 a rs with None -> Stuck
      | Some addr ->
        (match storev chunk m addr (rs r1) with None -> Stuck
          | Some aa -> Next (nextinstr_nf sz (undef_regs destroyed rs), aa)));;

let rec testVal64
  t rs v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint _ -> Vundef
      | Vlong n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint _ -> Vundef
          | Vlong n2 ->
            (let v =
               (match eval_testcond t rs with None -> Vundef
                 | Some true -> Vlong n2 | Some false -> Vlong n1)
               in
             let v1a =
               (match v with Vundef -> Vundef | Vbyte _ -> Vundef
                 | Vshort _ -> Vundef | Vint _ -> Vundef | Vlong a -> Vlong a)
               in
              v1a)));;

let rec testVal32
  t rs v1 v2 =
    (match v1 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
      | Vint n1 ->
        (match v2 with Vundef -> Vundef | Vbyte _ -> Vundef | Vshort _ -> Vundef
          | Vint n2 ->
            (let v =
               (match eval_testcond t rs with None -> Vundef
                 | Some true -> Vint n2 | Some false -> Vint n1)
               in
             let v1a =
               (match v with Vundef -> Vundef | Vbyte _ -> Vundef
                 | Vshort _ -> Vundef | Vint a -> Vint a | Vlong _ -> Vundef)
               in
              v1a)
          | Vlong _ -> Vundef)
      | Vlong _ -> Vundef);;

let rec exec_push
  sz chunk m rs v =
    (let nsp = sub64 (rs (IR RSP)) (vlong_of_memory_chunk chunk) in
      (match nsp with Vundef -> Stuck | Vbyte _ -> Stuck | Vshort _ -> Stuck
        | Vint _ -> Stuck
        | Vlong addr ->
          (match storev chunk m addr v with None -> Stuck
            | Some a ->
              Next (nextinstr_nf sz (fun_upd equal_preg rs (IR RSP) nsp),
                     a))));;

let rec exec_load
  sz chunk m a rs rd =
    (match eval_addrmode64 a rs with None -> Stuck
      | Some addr ->
        (match loadv chunk m addr with None -> Stuck
          | Some v -> Next (nextinstr_nf sz (fun_upd equal_preg rs rd v), m)));;

let rec exec_call
  sz chunk m rs v =
    (let nsp = sub64 (rs (IR RSP)) (vlong_of_memory_chunk chunk) in
      (match nsp with Vundef -> Stuck | Vbyte _ -> Stuck | Vshort _ -> Stuck
        | Vint _ -> Stuck
        | Vlong addr ->
          (match storev M64 m addr (add64 (rs PC) (Vlong sz)) with None -> Stuck
            | Some ma ->
              (let rs1 = fun_upd equal_preg rs (IR RSP) nsp in
                Next (fun_upd equal_preg rs1 PC (add64 (rs PC) v), ma)))));;

let rec exec_instr
  i sz rs m =
    (match i
      with Pmovl_rr (rd, r1) ->
        Next (nextinstr sz (fun_upd equal_preg rs (IR rd) (rs (IR r1))), m)
      | Pmovq_rr (rd, r1) ->
        Next (nextinstr sz (fun_upd equal_preg rs (IR rd) (rs (IR r1))), m)
      | Pmovl_ri (rd, n) ->
        Next (nextinstr sz (fun_upd equal_preg rs (IR rd) (Vint n)), m)
      | Pmovq_ri (rd, n) ->
        Next (nextinstr sz (fun_upd equal_preg rs (IR rd) (Vlong n)), m)
      | Pmov_rm (rd, a, c) -> exec_load sz c m a rs (IR rd)
      | Pmov_mr (a, r1, c) -> exec_store sz c m a rs (IR r1) []
      | Pmov_mi (a, n, c) ->
        (match eval_addrmode64 a rs with None -> Stuck
          | Some addr ->
            (match storev c m addr (Vint n) with None -> Stuck
              | Some aa -> Next (nextinstr_nf sz rs, aa)))
      | Pcmovl (t, rd, r1) ->
        Next (nextinstr sz
                (fun_upd equal_preg rs (IR rd)
                  (testVal32 t rs (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pcmovq (t, rd, r1) ->
        Next (nextinstr sz
                (fun_upd equal_preg rs (IR rd)
                  (testVal64 t rs (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pxchgq_rr (rd, r1) ->
        (let tmp = rs (IR rd) in
         let rs1 = fun_upd equal_preg rs (IR rd) (rs (IR r1)) in
          Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR r1) tmp), m))
      | Pxchgq_rm (r1, a, _) ->
        (match eval_addrmode64 a rs with None -> Stuck
          | Some addr ->
            (match loadv M64 m addr with None -> Stuck
              | Some v ->
                (let tmp = rs (IR r1) in
                  (match storev M64 m addr tmp with None -> Stuck
                    | Some aa ->
                      Next (nextinstr_nf sz (fun_upd equal_preg rs (IR r1) v),
                             aa)))))
      | Pmovsl_rr (rd, r1) ->
        Next (nextinstr sz
                (fun_upd equal_preg rs (IR rd) (longofints (rs (IR r1)))),
               m)
      | Pcdq ->
        Next (nextinstr sz
                (fun_upd equal_preg rs (IR RDX) (signex32 (rs (IR RAX)))),
               m)
      | Pcqo ->
        Next (nextinstr sz
                (fun_upd equal_preg rs (IR RDX) (signex64 (rs (IR RAX)))),
               m)
      | Pleaq (rd, a) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (eval_addrmode64_val a rs)),
               m)
      | Pnegl rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (neg32 (rs (IR rd)))),
               m)
      | Pnegq rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (neg64 (rs (IR rd)))),
               m)
      | Paddq_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (add64 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Paddl_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (add32 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Paddl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (add32 (rs (IR rd)) (Vint n))),
               m)
      | Paddw_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (add16 (rs (IR rd)) (Vshort n))),
               m)
      | Paddq_mi (a, n, c) ->
        (match eval_addrmode64 a rs with None -> Stuck
          | Some addr ->
            (match loadv c m addr with None -> Stuck
              | Some v ->
                (match
                  storev c m addr
                    (add64 v
                      (Vlong
                        (signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          n)))
                  with None -> Stuck
                  | Some aa -> Next (nextinstr_nf sz rs, aa))))
      | Psubl_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (sub32 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Psubq_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (sub64 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Psubl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (sub32 (rs (IR rd)) (Vint n))),
               m)
      | Pmull_r r1 ->
        (let rs1 =
           fun_upd equal_preg rs (IR RAX) (mul32 (rs (IR RAX)) (rs (IR r1))) in
          Next (nextinstr_nf sz
                  (fun_upd equal_preg rs1 (IR RDX)
                    (mulhu32 (rs (IR RAX)) (rs (IR r1)))),
                 m))
      | Pmulq_r r1 ->
        (let rs1 =
           fun_upd equal_preg rs (IR RAX) (mul64 (rs (IR RAX)) (rs (IR r1))) in
          Next (nextinstr_nf sz
                  (fun_upd equal_preg rs1 (IR RDX)
                    (mulhu64 (rs (IR RAX)) (rs (IR r1)))),
                 m))
      | Pimull_r r1 ->
        (let rs1 =
           fun_upd equal_preg rs (IR RAX) (mul32 (rs (IR RAX)) (rs (IR r1))) in
          Next (nextinstr_nf sz
                  (fun_upd equal_preg rs1 (IR RDX)
                    (mulhs32 (rs (IR RAX)) (rs (IR r1)))),
                 m))
      | Pimulq_r r1 ->
        (let rs1 =
           fun_upd equal_preg rs (IR RAX) (mul64 (rs (IR RAX)) (rs (IR r1))) in
          Next (nextinstr_nf sz
                  (fun_upd equal_preg rs1 (IR RDX)
                    (mulhs64 (rs (IR RAX)) (rs (IR r1)))),
                 m))
      | Pdivl_r r1 ->
        (match divmod32u (rs (IR RDX)) (rs (IR RAX)) (rs (IR r1))
          with None -> Stuck | Some (Vundef, _) -> Stuck
          | Some (Vbyte _, _) -> Stuck | Some (Vshort _, _) -> Stuck
          | Some (Vint _, Vundef) -> Stuck | Some (Vint _, Vbyte _) -> Stuck
          | Some (Vint _, Vshort _) -> Stuck
          | Some (Vint q, Vint r) ->
            (let rs1 = fun_upd equal_preg rs (IR RAX) (Vint q) in
              Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR RDX) (Vint r)),
                     m))
          | Some (Vint _, Vlong _) -> Stuck | Some (Vlong _, _) -> Stuck)
      | Pdivq_r r1 ->
        (match divmod64u (rs (IR RDX)) (rs (IR RAX)) (rs (IR r1))
          with None -> Stuck | Some (Vundef, _) -> Stuck
          | Some (Vbyte _, _) -> Stuck | Some (Vshort _, _) -> Stuck
          | Some (Vint _, _) -> Stuck | Some (Vlong _, Vundef) -> Stuck
          | Some (Vlong _, Vbyte _) -> Stuck | Some (Vlong _, Vshort _) -> Stuck
          | Some (Vlong _, Vint _) -> Stuck
          | Some (Vlong q, Vlong r) ->
            (let rs1 = fun_upd equal_preg rs (IR RAX) (Vlong q) in
              Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR RDX) (Vlong r)),
                     m)))
      | Pidivl_r r1 ->
        (match divmod32s (rs (IR RDX)) (rs (IR RAX)) (rs (IR r1))
          with None -> Stuck | Some (Vundef, _) -> Stuck
          | Some (Vbyte _, _) -> Stuck | Some (Vshort _, _) -> Stuck
          | Some (Vint _, Vundef) -> Stuck | Some (Vint _, Vbyte _) -> Stuck
          | Some (Vint _, Vshort _) -> Stuck
          | Some (Vint q, Vint r) ->
            (let rs1 = fun_upd equal_preg rs (IR RAX) (Vint q) in
              Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR RDX) (Vint r)),
                     m))
          | Some (Vint _, Vlong _) -> Stuck | Some (Vlong _, _) -> Stuck)
      | Pidivq_r r1 ->
        (match divmod64s (rs (IR RDX)) (rs (IR RAX)) (rs (IR r1))
          with None -> Stuck | Some (Vundef, _) -> Stuck
          | Some (Vbyte _, _) -> Stuck | Some (Vshort _, _) -> Stuck
          | Some (Vint _, _) -> Stuck | Some (Vlong _, Vundef) -> Stuck
          | Some (Vlong _, Vbyte _) -> Stuck | Some (Vlong _, Vshort _) -> Stuck
          | Some (Vlong _, Vint _) -> Stuck
          | Some (Vlong q, Vlong r) ->
            (let rs1 = fun_upd equal_preg rs (IR RAX) (Vlong q) in
              Next (nextinstr_nf sz (fun_upd equal_preg rs1 (IR RDX) (Vlong r)),
                     m)))
      | Pandl_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (and32 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pandl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (and32 (rs (IR rd)) (Vint n))),
               m)
      | Pandq_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (and64 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Porl_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (or32 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Porl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (or32 (rs (IR rd)) (Vint n))),
               m)
      | Porq_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (or64 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pxorl_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (xor32 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pxorq_rr (rd, r1) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (xor64 (rs (IR rd)) (rs (IR r1)))),
               m)
      | Pxorl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (xor32 (rs (IR rd)) (Vint n))),
               m)
      | Pshll_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (shl32 (rs (IR rd)) (Vbyte n))),
               m)
      | Pshlq_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (shl64 (rs (IR rd)) (Vbyte n))),
               m)
      | Pshll_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (shl32 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Pshlq_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (shl64 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Pshrl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (shr32 (rs (IR rd)) (Vbyte n))),
               m)
      | Pshrq_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (shr64 (rs (IR rd)) (Vbyte n))),
               m)
      | Pshrl_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (shr32 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Pshrq_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (shr64 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Psarl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (sar32 (rs (IR rd)) (Vbyte n))),
               m)
      | Psarq_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (sar64 (rs (IR rd)) (Vbyte n))),
               m)
      | Psarl_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (sar32 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Psarq_r rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd)
                  (sar64 (rs (IR rd)) (rs (IR RCX)))),
               m)
      | Prolw_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (rol16 (rs (IR rd)) (Vbyte n))),
               m)
      | Prorl_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (ror32 (rs (IR rd)) (Vbyte n))),
               m)
      | Prorq_ri (rd, n) ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (ror64 (rs (IR rd)) (Vbyte n))),
               m)
      | Pbswapl rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (bswap32 (rs (IR rd)))),
               m)
      | Pbswapq rd ->
        Next (nextinstr_nf sz
                (fun_upd equal_preg rs (IR rd) (bswap64 (rs (IR rd)))),
               m)
      | Ppushl_r r1 -> exec_push sz M32 m rs (rs (IR r1))
      | Ppushl_i n ->
        exec_push sz M32 m rs
          (Vint (cast (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                  n))
      | Ppushq_m (a, _) ->
        (match eval_addrmode64 a rs with None -> Stuck
          | Some addr ->
            (match loadv M64 m addr with None -> Stuck
              | Some aa -> exec_push sz M64 m rs aa))
      | Ppopl rd -> exec_pop sz M32 m rs (IR rd)
      | Ptestl_rr (r1, r2) ->
        Next (nextinstr sz
                (compare_ints (and32 (rs (IR r1)) (rs (IR r2)))
                  (Vint (zero_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                  rs),
               m)
      | Ptestq_rr (r1, r2) ->
        Next (nextinstr sz
                (compare_longs (and64 (rs (IR r1)) (rs (IR r2)))
                  (Vlong
                    (zero_word
                      (len_bit0
                        (len_bit0
                          (len_bit0
                            (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                  rs),
               m)
      | Ptestl_ri (rd, n) ->
        Next (nextinstr sz
                (compare_ints (and32 (rs (IR rd)) (Vint n))
                  (Vint (zero_word
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
                  rs),
               m)
      | Ptestq_ri (rd, n) ->
        Next (nextinstr sz
                (compare_longs
                  (and64 (rs (IR rd))
                    (Vlong
                      (cast (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        n)))
                  (Vlong
                    (zero_word
                      (len_bit0
                        (len_bit0
                          (len_bit0
                            (len_bit0 (len_bit0 (len_bit0 len_num1))))))))
                  rs),
               m)
      | Pcmpl_rr (r1, r2) ->
        Next (nextinstr sz (compare_ints (rs (IR r1)) (rs (IR r2)) rs), m)
      | Pcmpq_rr (r1, r2) ->
        Next (nextinstr sz (compare_longs (rs (IR r1)) (rs (IR r2)) rs), m)
      | Pcmpl_ri (r1, n) ->
        Next (nextinstr sz (compare_ints (rs (IR r1)) (Vint n) rs), m)
      | Pcmpq_ri (r1, n) ->
        Next (nextinstr sz
                (compare_longs (rs (IR r1))
                  (Vlong
                    (cast (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      n))
                  rs),
               m)
      | Pjcc (t, d) ->
        (match eval_testcond t rs with None -> Stuck
          | Some true ->
            Next (nextinstr
                    (plus_word
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (signed_cast
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        d)
                      sz)
                    rs,
                   m)
          | Some false -> Next (nextinstr sz rs, m))
      | Pjmp d ->
        Next (nextinstr
                (plus_word
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  (signed_cast
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    d)
                  sz)
                rs,
               m)
      | Pcall_r r1 -> exec_call sz M64 m rs (rs (IR r1))
      | Pcall_i d ->
        exec_call sz M64 m rs
          (Vlong
            (signed_cast
              (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
              (len_bit0
                (len_bit0 (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
              d))
      | Pret -> exec_ret sz M64 m rs | Pnop -> Next (nextinstr sz rs, m)
      | P -> Stuck);;

let rec x64_step
  l st =
    (match st
      with Next (rs, m) ->
        (match rs PC with Vundef -> Stuck | Vbyte _ -> Stuck | Vshort _ -> Stuck
          | Vint _ -> Stuck
          | Vlong v ->
            (match
              x64_decode
                (the_nat
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                  v)
                l
              with None -> Stuck
              | Some (sz, ins) ->
                exec_instr ins
                  (of_nat
                    (len_bit0
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                    sz)
                  rs m))
      | Stuck -> Stuck);;

let rec intlist_to_reg_ir_32
  lbin lr =
    (match x64_decode Zero_nat lbin with None -> (fun _ -> Vundef)
      | Some (_, ins) ->
        (fun a ->
          (match a
            with RAX ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr Zero_nat))
            | RBX ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr one_nat))
            | RCX ->
              (match ins
                with Pmovl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmovq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmovl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmovq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmov_rm (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmov_mr (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmov_mi (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmovl (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmovq (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pxchgq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pxchgq_rm (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmovsl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcdq ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcqo ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pleaq (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pnegl _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pnegq _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Paddq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Paddl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Paddl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Paddw_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Paddq_mi (_, _, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psubl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psubq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psubl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmull_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pmulq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pimull_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pimulq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pdivl_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pdivq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pidivl_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pidivq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pandl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pandl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pandq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Porl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Porl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Porq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pxorl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pxorq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pxorl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshll_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshlq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshll_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshlq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshrl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshrq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pshrl_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshrq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psarl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psarq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Psarl_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psarq_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Prolw_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Prorl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Prorq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pbswapl _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pbswapq _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ppushl_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ppushl_i _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ppushq_m (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ppopl _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ptestl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ptestq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ptestl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Ptestq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmpl_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmpq_rr (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmpl_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcmpq_ri (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pjcc (_, _) ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pjmp _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcall_r _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pcall_i _ ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pret ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | Pnop ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One))))
                | P ->
                  Vint (of_int
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (nth lr (nat_of_num (Bit0 One)))))
            | RDX ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 One))))
            | RSI ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit0 One)))))
            | RDI ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit0 One)))))
            | RBP ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit1 One)))))
            | RSP ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit1 One)))))
            | R8 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit0 (Bit0 One))))))
            | R9 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit0 (Bit0 One))))))
            | R10 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit1 (Bit0 One))))))
            | R11 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit1 (Bit0 One))))))
            | R12 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit0 (Bit1 One))))))
            | R13 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit0 (Bit1 One))))))
            | R14 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit0 (Bit1 (Bit1 One))))))
            | R15 ->
              Vint (of_int
                     (len_bit0
                       (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                     (nth lr (nat_of_num (Bit1 (Bit1 (Bit1 One)))))))));;

let rec intlist_to_reg_ir_16
  lbin lr =
    (match x64_decode Zero_nat lbin with None -> (fun _ -> Vundef)
      | Some (_, _) ->
        (fun a ->
          (match a
            with RAX ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr Zero_nat))
            | RBX ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr one_nat))
            | RCX ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 One))))
            | RDX ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 One))))
            | RSI ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit0 One)))))
            | RDI ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit0 One)))))
            | RBP ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit1 One)))))
            | RSP ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit1 One)))))
            | R8 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit0 (Bit0 One))))))
            | R9 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit0 (Bit0 One))))))
            | R10 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit1 (Bit0 One))))))
            | R11 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit1 (Bit0 One))))))
            | R12 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit0 (Bit1 One))))))
            | R13 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit0 (Bit1 One))))))
            | R14 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit0 (Bit1 (Bit1 One))))))
            | R15 ->
              Vshort
                (of_int (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))
                  (nth lr (nat_of_num (Bit1 (Bit1 (Bit1 One)))))))));;

let rec intlist_to_reg_ir
  lbin lr =
    (match x64_decode Zero_nat lbin with None -> (fun _ -> Vundef)
      | Some (_, ins) ->
        (fun a ->
          (match a
            with RAX ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr Zero_nat))
            | RBX ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr one_nat))
            | RCX ->
              (match ins
                with Pmovl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmovq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmovl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmovq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmov_rm (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmov_mr (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmov_mi (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmovl (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmovq (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pxchgq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pxchgq_rm (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmovsl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcdq ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcqo ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pleaq (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pnegl _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pnegq _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Paddq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Paddl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Paddl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Paddw_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Paddq_mi (_, _, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psubl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psubq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psubl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmull_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pmulq_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pimull_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pimulq_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pdivl_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pdivq_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pidivl_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pidivq_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pandl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pandl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pandq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Porl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Porl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Porq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pxorl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pxorq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pxorl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshll_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshlq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshll_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshlq_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshrl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshrq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshrl_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pshrq_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psarl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psarq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psarl_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Psarq_r _ ->
                  Vbyte (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (nth lr (nat_of_num (Bit0 One))))
                | Prolw_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Prorl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Prorq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pbswapl _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pbswapq _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ppushl_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ppushl_i _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ppushq_m (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ppopl _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ptestl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ptestq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ptestl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Ptestq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmpl_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmpq_rr (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmpl_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcmpq_ri (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pjcc (_, _) ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pjmp _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcall_r _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pcall_i _ ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pret ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | Pnop ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One))))
                | P ->
                  Vlong (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0
                                (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                          (nth lr (nat_of_num (Bit0 One)))))
            | RDX ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 One))))
            | RSI ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit0 One)))))
            | RDI ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit0 One)))))
            | RBP ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit1 One)))))
            | RSP ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit1 One)))))
            | R8 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit0 (Bit0 One))))))
            | R9 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit0 (Bit0 One))))))
            | R10 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit1 (Bit0 One))))))
            | R11 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit1 (Bit0 One))))))
            | R12 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit0 (Bit1 One))))))
            | R13 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit0 (Bit1 One))))))
            | R14 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit0 (Bit1 (Bit1 One))))))
            | R15 ->
              Vlong (of_int
                      (len_bit0
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      (nth lr (nat_of_num (Bit1 (Bit1 (Bit1 One)))))))));;

let rec intlist_to_reg_cr
  lc = (fun a ->
         (match a
           with ZF ->
             Vint (of_int
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (nth lc Zero_nat))
           | CF ->
             Vint (of_int
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (nth lc one_nat))
           | PF ->
             Vint (of_int
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (nth lc (nat_of_num (Bit0 One))))
           | SF ->
             Vint (of_int
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (nth lc (nat_of_num (Bit1 One))))
           | OF ->
             Vint (of_int
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    (nth lc (nat_of_num (Bit0 (Bit0 One)))))));;

let rec intlist_to_reg_map
  mode lbin lc lr =
    (fun a ->
      (match a
        with PC ->
          Vlong (zero_word
                  (len_bit0
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))))
        | IR ir ->
          (match mode with D64 -> intlist_to_reg_ir lbin lr ir
            | D32 -> intlist_to_reg_ir_32 lbin lr ir
            | D16 -> intlist_to_reg_ir_16 lbin lr ir)
        | CR aa -> intlist_to_reg_cr lc aa));;

let rec u8_list_to_mem
  l = (fun i ->
        (if less_nat
              (the_nat
                (len_bit0
                  (len_bit0
                    (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                i)
              (size_list l)
          then Some (nth l
                      (the_nat
                        (len_bit0
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        i))
          else None));;

let rec int_to_u8_list
  lp = map (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))) lp;;

let i64_MIN
  = (Neg (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0
 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))));;

let rec num_to_int64 (n: num) : int64 =
  match n with
  | One -> 1L
  | Bit0 m -> Int64.mul 2L (num_to_int64 m)
  | Bit1 m -> Int64.add (Int64.mul 2L (num_to_int64 m)) 1L     

let myint_to_int64 (mi: myint) : int64 =
  match mi with
  | Zero_int -> 0L
  | Pos n -> num_to_int64 n
  | Neg n -> Int64.neg (num_to_int64 n)

let rec num_of_int64 (n: int64) =
  if n = 1L then One
  else if Int64.rem n 2L = 0L then Bit0 (num_of_int64 (Int64.div n 2L))
  else Bit1 (num_of_int64 (Int64.div n 2L))


let int64_to_myint (n: int64) =
  if n = 0L then Zero_int
  else if n > 0L then  Pos (num_of_int64 (n))
  else if n = 0x8000000000000000L then i64_MIN
  else Neg (num_of_int64 (Int64.sub 0L n))

let int64_list_to_myint_list lst =
  List.map int64_to_myint lst


let ireg_table = [
  ("RAX", RAX); ("RBX", RBX); ("RCX", RCX); ("RDX", RDX);
  ("RSI", RSI); ("RDI", RDI); ("RBP", RBP); ("RSP", RSP);
  ("R8",  R8 ); ("R9",  R9 ); ("R10", R10); ("R11", R11);
  ("R12", R12); ("R13", R13); ("R14", R14); (*("R15", R15)*)
]

let crbit_table = [
  ("ZF", ZF); ("CF", CF); ("PF", PF); ("SF", SF); ("OF", OF)
]

let preg_list : (string * preg) list =
  [ ("PC",  PC); ]
  @ List.map (fun (s, r) -> ("IR." ^ s, IR r))  ireg_table
  @ List.map (fun (s, f) -> ("CR." ^ s, CR f))  crbit_table

let len8  = len_bit0 (len_bit0 (len_bit0 len_num1)) 
let len16 = len_bit0 len8
let len32 = len_bit0 len16
let len64 = len_bit0 len32

let int64_of_vala (v : vala) : (int64 option) =
  match v with
  | Vundef      -> None
  | Vbyte  w    -> Some (myint_to_int64 (the_int len8  w))
  | Vshort w    -> Some (myint_to_int64 (the_int len16 w))
  | Vint   w    -> Some (myint_to_int64 (the_int len32 w))
  | Vlong  w    -> Some (myint_to_int64 (the_int len64 w))

let print_pregmap (rs : preg -> vala) : unit =
  List.iter (fun (name, r) ->
    match int64_of_vala (rs r) with
    | None ->
        Printf.printf "%-6s : <undef>\n" name
    | Some v ->
        let fmt : ('a, 'b, 'c, unit, unit, unit) format6 =
          match r with
          | PC | IR _       -> "%-6s : %Ld\n"
          | CR _            -> "%-6s : %Ld\n"
        in
        Printf.printf fmt name v
  ) preg_list


let return_pregmap (rs : preg -> vala) : int64 list =
List.fold_left
  (fun acc (_, r) ->
      match int64_of_vala (rs r) with
      | None   -> 0x0L :: acc              
      | Some v -> v :: acc) 
  [] 
  preg_list
|> List.rev

      
let rec x64_step_test
  bits lbin lc lr lm =
    (let mode =
       (if equal_int bits (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))
         then D64
         else (if equal_int bits (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
                then D32 else D16))
       in
     let res =
       x64_step (int_to_u8_list lbin)
         (Next (intlist_to_reg_map mode (int_to_u8_list lbin) lc lr,
                 u8_list_to_mem (int_to_u8_list lm)))
       in
      (match res  with
       | Stuck -> []
       | Next (rs, m) -> (return_pregmap rs)
      ));;

end;; (*struct x64_step_test*)