module X64_encode : sig
  type num
  type myint
  type nat
  type 'a word
  type 'a bit0
  type num1
  type ireg
  type memory_chunk
  type addrmode
  type testcond
  type instruction
  val x64_encode : instruction -> (num1 bit0 bit0 bit0 word list) option
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

type ireg = RAX | RBX | RCX | RDX | RSI | RDI | RBP | RSP | R8 | R9 | R10 | R11
  | R12 | R13 | R14 | R15;;

type memory_chunk = M8 | M16 | M32 | M64;;

type addrmode =
  Addrmode of
    ireg option * (ireg * num1 bit0 bit0 bit0 word) option *
      num1 bit0 bit0 bit0 bit0 bit0 word;;

type testcond = Cond_e | Cond_ne | Cond_b | Cond_be | Cond_ae | Cond_a | Cond_l
  | Cond_le | Cond_ge | Cond_g | Cond_p | Cond_np;;

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

let rec cast _B _A
  w = Word (take_bit_int (len_of _A.len0_len Type) (the_int _B w));;

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

let rec signed_cast _B _A
  w = Word (take_bit_int (len_of _A.len0_len Type) (the_signed_int _B w));;

let rec u8_of_cond
  = function
    Cond_b -> of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One))
    | Cond_ae ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))
    | Cond_e ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit0 One)))
    | Cond_ne ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 One)))
    | Cond_be ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit1 One)))
    | Cond_a ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit1 One)))
    | Cond_p ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 (Bit0 One))))
    | Cond_np ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit0 One))))
    | Cond_l ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit0 (Bit1 One))))
    | Cond_ge ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit0 (Bit1 One))))
    | Cond_le ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 (Bit1 One))))
    | Cond_g ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit1 One))));;

let rec zero_word _A = Word Zero_int;;

let rec u8_of_ireg
  = function RAX -> zero_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
    | RCX -> one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))
    | RDX -> of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 One))
    | RBX -> of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 One))
    | RSP ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit0 One)))
    | RBP ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit0 One)))
    | RSI ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit0 (Bit1 One)))
    | RDI ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1))) (Pos (Bit1 (Bit1 One)))
    | R8 -> of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (Pos (Bit0 (Bit0 (Bit0 One))))
    | R9 -> of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
              (Pos (Bit1 (Bit0 (Bit0 One))))
    | R10 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 (Bit0 One))))
    | R11 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit0 One))))
    | R12 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit0 (Bit1 One))))
    | R13 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit0 (Bit1 One))))
    | R14 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit0 (Bit1 (Bit1 One))))
    | R15 ->
        of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit1 One))));;

let rec u8_of_bool
  b = (match b with true -> one_worda (len_bit0 (len_bit0 (len_bit0 len_num1)))
        | false -> zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))));;

let rec and_word _A v w = Word (and_int (the_int _A v) (the_int _A w));;

let rec equal_memory_chunk x0 x1 = match x0, x1 with M32, M64 -> false
                             | M64, M32 -> false
                             | M16, M64 -> false
                             | M64, M16 -> false
                             | M16, M32 -> false
                             | M32, M16 -> false
                             | M8, M64 -> false
                             | M64, M8 -> false
                             | M8, M32 -> false
                             | M32, M8 -> false
                             | M8, M16 -> false
                             | M16, M8 -> false
                             | M64, M64 -> true
                             | M32, M32 -> true
                             | M16, M16 -> true
                             | M8, M8 -> true;;

let rec drop_bit_word _A n w = Word (drop_bit_int n (the_int _A w));;

let rec minus_word _A
  a b = of_int _A (minus_inta (the_int _A a) (the_int _A b));;

let rec bitfield_extract _A
  pos width n =
    and_word _A
      (minus_word _A (power (power_word _A) (of_int _A (Pos (Bit0 One))) width)
        (one_worda _A))
      (drop_bit_word _A pos n);;

let rec push_bit_word _A
  n w = times_worda _A w
          (power (power_word _A) (of_int _A (Pos (Bit0 One))) n);;

let rec or_word _A v w = Word (or_int (the_int _A v) (the_int _A w));;

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

let rec construct_modsib_to_u8
  op1 op2 op3 =
    bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
      (nat_of_num (Bit0 (Bit1 One))) (nat_of_num (Bit0 One))
      (bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
        (nat_of_num (Bit1 One)) (nat_of_num (Bit1 One))
        (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
          (nat_of_num (Bit1 One)) op3)
        (bitfield_extract (len_bit0 (len_bit0 (len_bit0 len_num1))) Zero_nat
          (nat_of_num (Bit1 One)) op2))
      op1;;

let rec uminus_word _A a = of_int _A (uminus_inta (the_int _A a));;

let rec construct_rex_to_u8
  w r x b =
    bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
      (nat_of_num (Bit0 (Bit0 One))) (nat_of_num (Bit0 (Bit0 One)))
      (bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
        (nat_of_num (Bit1 One)) one_nat
        (bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (nat_of_num (Bit0 One)) one_nat
          (bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1))) one_nat
            one_nat (u8_of_bool b) (u8_of_bool x))
          (u8_of_bool r))
        (u8_of_bool w))
      (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
        (Pos (Bit0 (Bit0 One))));;

let rec less_eq_word _A a b = less_eq_int (the_int _A a) (the_int _A b);;

let rec equal_word _A v w = equal_int (the_int _A v) (the_int _A w);;

let rec less_word _A a b = less_int (the_int _A a) (the_int _A b);;

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

let rec x64_encode
  ins = (match ins
          with Pmovl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pmovq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Pmovl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Pmovq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit1 One))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 (Bit1 (Bit0 One)))))))))
                 (u8_of_ireg rd)
               in
              Some ([rex; op] @ u8_list_of_u64 n))
          | Pmov_rm (_, Addrmode (None, _, _), _) -> None
          | Pmov_rm (rd, Addrmode (Some rb, None, dis), c) ->
            (let rex =
               construct_rex_to_u8 (equal_memory_chunk c M64)
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rb)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
              (if less_eq_word
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    dis (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 One)))))))) ||
                    less_eq_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (uminus_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))
                      dis
                then (let disa =
                        signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0 (len_bit0 (len_bit0 len_num1))) dis
                        in
                      let rop =
                        construct_modsib_to_u8
                          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (u8_of_ireg rd) (u8_of_ireg rb)
                        in
                       (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             rex (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                         then (match c with M8 -> None | M16 -> None
                                | M32 ->
                                  Some [of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M64 -> None)
                         else (match c with M8 -> None | M16 -> None
                                | M32 ->
                                  Some [rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M64 ->
                                  Some [rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa])))
                else (if not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 (Bit1 One)))))
                               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (Pos (Bit0 (Bit0 One)))))
                       then (let rop =
                               construct_modsib_to_u8
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 One)))
                                 (u8_of_ireg rd) (u8_of_ireg rb)
                               in
                              (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    rex (of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                                then (match c with M8 -> None | M16 -> None
                                       | M32 ->
 Some ([of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis)
                                       | M64 -> None)
                                else (match c with M8 -> None | M16 -> None
                                       | M32 ->
 Some ([rex; of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis)
                                       | M64 ->
 Some ([rex; of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis))))
                       else None)))
          | Pmov_rm (rd, Addrmode (Some rb, Some (ri, scale), dis), c) ->
            (if less_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
                  scale ||
                  not (equal_memory_chunk c M64)
              then None
              else (let rex =
                      construct_rex_to_u8 true
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rd)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg ri)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      in
                    let op =
                      of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit1 (Bit0
   (Bit1 (Bit0 (Bit0 (Bit0 One))))))))
                      in
                    let rop =
                      construct_modsib_to_u8
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 One)))
                        (u8_of_ireg rd)
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 One))))
                      in
                    let sib =
                      construct_modsib_to_u8 scale (u8_of_ireg ri)
                        (u8_of_ireg rb)
                      in
                     Some ([rex; op; rop; sib] @ u8_list_of_u32 dis)))
          | Pmov_mr (Addrmode (None, _, _), _, _) -> None
          | Pmov_mr (Addrmode (Some rb, None, dis), r1, c) ->
            (let rex =
               construct_rex_to_u8 (equal_memory_chunk c M64)
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rb)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
              (if less_eq_word
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    dis (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 One)))))))) ||
                    less_eq_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (uminus_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))
                      dis
                then (let disa =
                        signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0 (len_bit0 (len_bit0 len_num1))) dis
                        in
                      let rop =
                        construct_modsib_to_u8
                          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (u8_of_ireg r1) (u8_of_ireg rb)
                        in
                       (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                             rex (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0
  (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                         then (match c
                                with M8 ->
                                  Some [of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M16 ->
                                  Some [of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 One)))))));
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M32 ->
                                  Some [of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M64 -> None)
                         else (match c
                                with M8 ->
                                  Some [rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M16 ->
                                  Some [of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 One)))))));
 rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M32 ->
                                  Some [rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa]
                                | M64 ->
                                  Some [rex;
 of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
   (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
 rop; disa])))
                else (if not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit1 (Bit1 One)))))
                               (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (Pos (Bit0 (Bit0 One)))))
                       then (let rop =
                               construct_modsib_to_u8
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 One)))
                                 (u8_of_ireg r1) (u8_of_ireg rb)
                               in
                              (if equal_word
                                    (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                    rex (of_int
  (len_bit0 (len_bit0 (len_bit0 len_num1)))
  (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                                then (match c with M8 -> None | M16 -> None
                                       | M32 ->
 Some ([of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
          (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis)
                                       | M64 -> None)
                                else (match c with M8 -> None | M16 -> None
                                       | M32 ->
 Some ([rex; of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis)
                                       | M64 ->
 Some ([rex; of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
               (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 One))))))));
         rop] @
        u8_list_of_u32 dis))))
                       else None)))
          | Pmov_mr (Addrmode (Some rb, Some (ri, scale), dis), r1, c) ->
            (if less_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
                  scale ||
                  not (equal_memory_chunk c M64)
              then None
              else (let rex =
                      construct_rex_to_u8 true
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg r1)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg ri)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      in
                    let op =
                      of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit0 (Bit0
   (Bit1 (Bit0 (Bit0 (Bit0 One))))))))
                      in
                    let rop =
                      construct_modsib_to_u8
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 One)))
                        (u8_of_ireg r1)
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 One))))
                      in
                    let sib =
                      construct_modsib_to_u8 scale (u8_of_ireg ri)
                        (u8_of_ireg rb)
                      in
                     Some ([rex; op; rop; sib] @ u8_list_of_u32 dis)))
          | Pmov_mi (_, _, M8) -> None | Pmov_mi (_, _, M16) -> None
          | Pmov_mi (_, _, M32) -> None
          | Pmov_mi (Addrmode (None, _, _), _, M64) -> None
          | Pmov_mi (Addrmode (Some rd, None, dis), n, M64) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
              (if less_eq_word
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    dis (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 One)))))))) ||
                    less_eq_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (uminus_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))
                      dis
                then (let disa =
                        signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0 (len_bit0 (len_bit0 len_num1))) dis
                        in
                      let rop =
                        construct_modsib_to_u8
                          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (u8_of_ireg rd)
                        in
                       Some ([rex; op; rop; disa] @ u8_list_of_u32 n))
                else (let rop =
                        construct_modsib_to_u8
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 One)))
                          (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (u8_of_ireg rd)
                        in
                       Some ([rex; op; rop] @
                              u8_list_of_u32 dis @ u8_list_of_u32 n))))
          | Pmov_mi (Addrmode (Some _, Some _, _), _, M64) -> None
          | Pcmovl (t, rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let ex =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 One))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit0 (Bit0 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                 (u8_of_cond t)
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg rd) (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [ex; op; rop] else Some [rex; ex; op; rop]))
          | Pcmovq (t, rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let ex =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 One))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit0 (Bit0 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                 (u8_of_cond t)
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg rd) (u8_of_ireg r1)
               in
              Some [rex; ex; op; rop])
          | Pxchgq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Pxchgq_rm (_, _, M8) -> None | Pxchgq_rm (_, _, M16) -> None
          | Pxchgq_rm (_, _, M32) -> None
          | Pxchgq_rm (_, Addrmode (None, _, _), M64) -> None
          | Pxchgq_rm (_, Addrmode (Some _, None, _), M64) -> None
          | Pxchgq_rm (r1, Addrmode (Some rb, Some (ri, scale), dis), M64) ->
            (if less_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
                  scale
              then None
              else (let rex =
                      construct_rex_to_u8 true
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg r1)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg ri)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      in
                    let op =
                      of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit1 (Bit1
   (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                      in
                    let rop =
                      construct_modsib_to_u8
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 One)))
                        (u8_of_ireg r1)
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 One))))
                      in
                    let sib =
                      construct_modsib_to_u8 scale (u8_of_ireg ri)
                        (u8_of_ireg rb)
                      in
                     Some ([rex; op; rop; sib] @ u8_list_of_u32 dis)))
          | Pmovsl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One)))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg rd) (u8_of_ireg r1)
               in
              Some [rex; op; rop])
          | Pcdq ->
            Some [of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 One))))))))]
          | Pcqo ->
            Some [of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 One)))))));
                   of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 One))))))))]
          | Pleaq (_, Addrmode (None, _, _)) -> None
          | Pleaq (rd, Addrmode (Some rb, None, dis)) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rb)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 One))))))))
               in
              (if less_eq_word
                    (len_bit0
                      (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                    dis (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit1 (Bit1 (Bit1
     (Bit1 (Bit1 (Bit1 One)))))))) ||
                    less_eq_word
                      (len_bit0
                        (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                      (uminus_word
                        (len_bit0
                          (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                        (of_int
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (Pos (Bit0 (Bit0 (Bit0
     (Bit0 (Bit0 (Bit0 (Bit0 One))))))))))
                      dis
                then (let disa =
                        signed_cast
                          (len_bit0
                            (len_bit0
                              (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                          (len_bit0 (len_bit0 (len_bit0 len_num1))) dis
                        in
                      let rop =
                        construct_modsib_to_u8
                          (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                          (u8_of_ireg rd) (u8_of_ireg rb)
                        in
                       Some [rex; op; rop; disa])
                else (let rop =
                        construct_modsib_to_u8
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 One)))
                          (u8_of_ireg rd) (u8_of_ireg rb)
                        in
                       Some ([rex; op; rop] @ u8_list_of_u32 dis))))
          | Pleaq (_, Addrmode (Some _, Some _, _)) -> None
          | Pnegl rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pnegq rd ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Paddq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op = one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))) in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Paddl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op = one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))) in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Paddl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Paddw_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit1
   (Bit1 (Bit0 (Bit0 (Bit1 One)))))));
                             op; rop] @
                            u8_list_of_u16 n)
                else Some ([of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                              (Pos (Bit0 (Bit1
   (Bit1 (Bit0 (Bit0 (Bit1 One)))))));
                             rex; op; rop] @
                            u8_list_of_u16 n)))
          | Paddq_mi (_, _, M8) -> None | Paddq_mi (_, _, M16) -> None
          | Paddq_mi (_, _, M32) -> None
          | Paddq_mi (Addrmode (None, _, _), _, M64) -> None
          | Paddq_mi (Addrmode (Some _, None, _), _, M64) -> None
          | Paddq_mi (Addrmode (Some rb, Some (ri, scale), dis), n, M64) ->
            (if less_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
                  scale
              then None
              else (let rex =
                      construct_rex_to_u8 true false
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg ri)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      in
                    let op =
                      of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit0 (Bit0
   (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                      in
                    let rop =
                      construct_modsib_to_u8
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 One)))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 One))))
                      in
                    let sib =
                      construct_modsib_to_u8 scale (u8_of_ireg ri)
                        (u8_of_ireg rb)
                      in
                     Some ([rex; op; rop; sib] @
                            u8_list_of_u32 dis @ u8_list_of_u32 n)))
          | Psubl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Psubq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Psubl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Pmull_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pmulq_r r1 ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg r1)
               in
              Some [rex; op; rop])
          | Pimull_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pimulq_r r1 ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg r1)
               in
              Some [rex; op; rop])
          | Pdivl_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pdivq_r r1 ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              Some [rex; op; rop])
          | Pidivl_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pidivq_r r1 ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              Some [rex; op; rop])
          | Pandl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pandl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Pandq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Porl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 One))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Porl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Porq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 One))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Pxorl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pxorq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit1 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Pxorl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit1 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Pshll_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop; imm] else Some [rex; op; rop; imm]))
          | Pshlq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              Some [rex; op; rop; imm])
          | Pshll_r rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pshlq_r rd ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Pshrl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop; imm] else Some [rex; op; rop; imm]))
          | Pshrq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              Some [rex; op; rop; imm])
          | Pshrl_r rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pshrq_r rd ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit0 One))))
                 (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Psarl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop; imm] else Some [rex; op; rop; imm]))
          | Psarq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              Some [rex; op; rop; imm])
          | Psarl_r rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Psarq_r rd ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Prolw_ri (rd, n) ->
            (let prefix =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit0 (Bit1 (Bit1 (Bit0 (Bit0 (Bit1 One)))))))
               in
             let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [prefix; op; rop; imm]
                else Some [prefix; rex; op; rop; imm]))
          | Prorl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop; imm] else Some [rex; op; rop; imm]))
          | Prorq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (one_worda (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
             let imm =
               cast (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (len_bit0 (len_bit0 (len_bit0 len_num1))) n
               in
              Some [rex; op; rop; imm])
          | Pbswapl rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let ex =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 One))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit1 One))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit1 One)))))))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [ex; op] else Some [rex; ex; op]))
          | Pbswapq rd ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let ex =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 One))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit1 One))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 (Bit1 One)))))))))
                 (u8_of_ireg rd)
               in
              Some [rex; ex; op])
          | Ppushl_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit1 One))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 One))))))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op] else Some [rex; op]))
          | Ppushl_i n ->
            (let rex = construct_rex_to_u8 true false false false in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 One)))))))
               in
              Some ([rex; op] @ u8_list_of_u32 n))
          | Ppushq_m (_, M8) -> None | Ppushq_m (_, M16) -> None
          | Ppushq_m (_, M32) -> None
          | Ppushq_m (Addrmode (None, _, _), M64) -> None
          | Ppushq_m (Addrmode (Some _, None, _), M64) -> None
          | Ppushq_m (Addrmode (Some rb, Some (ri, scale), dis), M64) ->
            (if less_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                  (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 One)))
                  scale
              then None
              else (let rex =
                      construct_rex_to_u8 true false
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg ri)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                        (not (equal_word
                               (len_bit0 (len_bit0 (len_bit0 len_num1)))
                               (and_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                 (u8_of_ireg rb)
                                 (of_int
                                   (len_bit0 (len_bit0 (len_bit0 len_num1)))
                                   (Pos (Bit0 (Bit0 (Bit0 One))))))
                               (zero_word
                                 (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                      in
                    let op =
                      of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (Pos (Bit1 (Bit1 (Bit1
   (Bit1 (Bit1 (Bit1 (Bit1 One))))))))
                      in
                    let rop =
                      construct_modsib_to_u8
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 One)))
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit1 One))))
                        (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (Pos (Bit0 (Bit0 One))))
                      in
                    let sib =
                      construct_modsib_to_u8 scale (u8_of_ireg ri)
                        (u8_of_ireg rb)
                      in
                     Some ([rex; op; rop; sib] @ u8_list_of_u32 dis)))
          | Ppopl rd ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit1 One))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit1 (Bit1 (Bit0 One))))))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op] else Some [rex; op]))
          | Ptestl_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Ptestq_rr (rd, r1) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg rd)
               in
              Some [rex; op; rop])
          | Ptestl_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Ptestq_ri (rd, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg rd)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit0 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))
                 (u8_of_ireg rd)
               in
              Some ([rex; op; rop] @ u8_list_of_u32 n))
          | Pcmpl_rr (r1, r2) ->
            (let rex =
               construct_rex_to_u8 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r2)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg r2)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pcmpq_rr (r1, r2) ->
            (let rex =
               construct_rex_to_u8 true
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
                 false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r2)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit1 One))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (u8_of_ireg r1) (u8_of_ireg r2)
               in
              Some [rex; op; rop])
          | Pcmpl_ri (r1, n) ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some ([op; rop] @ u8_list_of_u32 n)
                else Some ([rex; op; rop] @ u8_list_of_u32 n)))
          | Pcmpq_ri (r1, n) ->
            (let rex =
               construct_rex_to_u8 true false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 (Bit1 One))))
                 (u8_of_ireg r1)
               in
              Some ([rex; op; rop] @ u8_list_of_u32 n))
          | Pjcc (t, d) ->
            (let ex =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 One))))
               in
             let op =
               bitfield_insert (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 Zero_nat (nat_of_num (Bit0 (Bit0 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One)))))))))
                 (u8_of_cond t)
               in
              Some ([ex; op] @
                     u8_list_of_u32
                       (cast (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         d)))
          | Pjmp d ->
            (let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit0 (Bit0 (Bit1 (Bit0 (Bit1 (Bit1 One))))))))
               in
              Some ([op] @
                     u8_list_of_u32
                       (cast (len_bit0
                               (len_bit0
                                 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         (len_bit0
                           (len_bit0 (len_bit0 (len_bit0 (len_bit0 len_num1)))))
                         d)))
          | Pcall_r r1 ->
            (let rex =
               construct_rex_to_u8 false false false
                 (not (equal_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                        (and_word (len_bit0 (len_bit0 (len_bit0 len_num1)))
                          (u8_of_ireg r1)
                          (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                            (Pos (Bit0 (Bit0 (Bit0 One))))))
                        (zero_word (len_bit0 (len_bit0 (len_bit0 len_num1))))))
               in
             let op =
               of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                 (Pos (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 (Bit1 One))))))))
               in
             let rop =
               construct_modsib_to_u8
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit1 One)))
                 (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                   (Pos (Bit0 One)))
                 (u8_of_ireg r1)
               in
              (if equal_word (len_bit0 (len_bit0 (len_bit0 len_num1))) rex
                    (of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                      (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 (Bit0 One))))))))
                then Some [op; rop] else Some [rex; op; rop]))
          | Pcall_i d ->
            Some ([of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                     (Pos (Bit0 (Bit0 (Bit0
(Bit1 (Bit0 (Bit1 (Bit1 One))))))))] @
                   u8_list_of_u32 d)
          | Pret ->
            Some [of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit1 (Bit1 (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 One))))))))]
          | Pnop ->
            Some [of_int (len_bit0 (len_bit0 (len_bit0 len_num1)))
                    (Pos (Bit0 (Bit0 (Bit0 (Bit0 (Bit1 (Bit0 (Bit0 One))))))))]
          | P -> None);;

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


let ( let* ) o f =
  match o with
  | None   -> None
  | Some x -> f x

type token = string

let split_ws (s : string) : token list =
  let rec aux i acc =
    match String.index_from_opt s i ' ' with
    | None ->
        let t = String.sub s i (String.length s - i) in
        if t = "" then List.rev acc else List.rev (t :: acc)
    | Some j ->
        let t = String.sub s i (j - i) |> String.trim in
        let acc' = if t = "" then acc else t :: acc in
        aux (j + 1) acc'
  in aux 0 []

let parse_ireg = function
  | "RAX" -> Some RAX | "RBX" -> Some RBX | "RCX" -> Some RCX
  | "RDX" -> Some RDX | "RSI" -> Some RSI | "RDI" -> Some RDI
  | "RBP" -> Some RBP | "RSP" -> Some RSP
  | "R8"  -> Some R8  | "R9"  -> Some R9
  | "R10" -> Some R10 | "R11" -> Some R11
  | "R12" -> Some R12 | "R13" -> Some R13
  | "R14" -> Some R14 | "R15" -> Some R15
  | _     -> None

let parse_cond = function
  | "e"  -> Some Cond_e| "ne" -> Some Cond_ne| "b"  -> Some Cond_b
  | "be" -> Some Cond_be| "ae" -> Some Cond_ae| "a"  -> Some Cond_a
  | "l"  -> Some Cond_l| "le" -> Some Cond_le| "ge" -> Some Cond_ge
  | "g"  -> Some Cond_g| "p"  -> Some Cond_p| "np" -> Some Cond_np
  | _ -> None

let len8  = len_bit0 (len_bit0 (len_bit0 len_num1)) 
let len16 = len_bit0 len8
let len32 = len_bit0 len16
let len64 = len_bit0 len32

let parse_u8_word (s:string) : (num1 bit0 bit0 bit0 word) option =
  try
    let n = int_of_string s in
    if n < 0 || n > 255 then None
    else
      let mi = int64_to_myint (Int64.of_int n) in
      Some (of_int len8 mi)
  with _ -> None

let parse_u16_word (s:string) : (num1 bit0 bit0 bit0 bit0 word) option =
  try
    let n = int_of_string s in
    if n < 0 || n > 0xFFFF then None
    else
      let mi = int64_to_myint (Int64.of_int n) in
      Some (of_int len16 mi)
  with _ -> None

let parse_u32_word (s:string) : (num1 bit0 bit0 bit0 bit0 bit0 word) option =
  try
    let n = Int64.of_string s in
    if n < 0L || n > 0xFFFF_FFFFL then None
    else Some (of_int len32 (int64_to_myint n))
  with _ -> None

let parse_u64_word (s:string) : (num1 bit0 bit0 bit0 bit0 bit0 bit0 word) option =
  try
    let n = Int64.of_string s in
    (*if n < 0L || n > 0x7FFF_FFFF_FFFF_FFFFL then None
    else*) Some (of_int len64 (int64_to_myint n))
  with _ -> None

let parse_ireg_option (s : string) : ireg option option =
  if s = "None" then Some None
  else
    match parse_ireg s with
    | Some reg -> Some (Some reg)
    | None -> None

let starts_with ~prefix s =
  let prefix_len = String.length prefix in
  String.length s >= prefix_len && String.sub s 0 prefix_len = prefix

let ends_with ~suffix s =
  let suffix_len = String.length suffix in
  let len = String.length s in
  len >= suffix_len && String.sub s (len - suffix_len) suffix_len = suffix

let parse_addrmode (s : string) : addrmode option =
  let prefix = "(Addrmode " in
  if starts_with ~prefix s && ends_with ~suffix:")" s then
    let inner =
      let len = String.length s in
      String.sub s (String.length prefix) (len - String.length prefix - 1)
    in
    (*Printf.eprintf "[DEBUG] raw inner content: %s\n%!" inner;*)
    let tokens = split_ws inner in
    (*Printf.eprintf "[DEBUG] split tokens: [%s]\n%!" (String.concat "; " tokens);*)
    match tokens with
    | base_str :: index_str :: disp_str :: [] ->
        (*Printf.eprintf "[DEBUG] base_str = %s\n[DEBUG] index_str = %s\n[DEBUG] disp_str = %s\n%!"
          base_str index_str disp_str;*)
        let* base = parse_ireg_option base_str in
        let index = None in
        let* disp = parse_u32_word disp_str in
        Some (Addrmode (base, index, disp))
    | _ ->
        (*Printf.eprintf "[DEBUG] token count mismatch\n%!";*)
        None
  else (
    (*Printf.eprintf "[DEBUG] not an Addrmode string: %s\n%!" s;*)
    None
  )



let parse_instruction (line : string) : instruction option =
  match split_ws line with
  | [] -> None
  | "Pleaq":: r_dest::rest ->
      let addr_str = String.concat " " rest in
        let* rd = parse_ireg r_dest in
        let* am = parse_addrmode addr_str in
        Some (Pleaq (rd, am))
  | opc :: rest ->            
    begin match opc, rest with
    | ("Pcdq" | "Pcqo") , [] -> 
      begin match opc with
        | "Pcqo" -> Some (Pcqo)
        | "Pcdq" -> Some (Pcdq)
        | _ -> None
      end

    | ("Pcmovq" | "Pcmovl"), [cond_str; r1; r2] ->
        let* cond = parse_cond cond_str in
        let* rd = parse_ireg r1 in
        let* rs = parse_ireg r2 in
        begin match opc with
        | "Pcmovq" -> Some (Pcmovq (cond, rd, rs))
        | "Pcmovl" -> Some (Pcmovl (cond, rd, rs))
        | _ -> None
        end
    | ("Pjmp"), [d] ->
        let* d = parse_u32_word d in
        begin match opc with
        | "Pjmp" -> Some (Pjmp d)
        | _ -> None
        end
    | ("Pjcc"), [cond_str; d] ->
      let* cond = parse_cond cond_str in
      let* d = parse_u32_word d in
      begin match opc with
      | "Pjcc" -> Some (Pjcc (cond, d))
      | _ -> None
      end
    
    | ("Paddw_ri") , [r1; imm16] ->
        let* rd   = parse_ireg r1       in
        let* imm  = parse_u16_word imm16 in
        begin match opc with
        | "Paddw_ri" -> Some (Paddw_ri (rd, imm))
        | _ -> None
        end

    | ("Pshlq_ri" | "Pshrq_ri" | "Psarq_ri" | "Prorq_ri" 
      |"Pshll_ri" | "Pshrl_ri" | "Psarl_ri" | "Prorl_ri"
      | "Prolw_ri"),
      [r1; imm8] ->
        let* rd   = parse_ireg r1     in
        let* imm  = parse_u8_word imm8 in
        begin match opc with
        | "Pshlq_ri" -> Some (Pshlq_ri (rd, imm))
        | "Pshrq_ri" -> Some (Pshrq_ri (rd, imm))
        | "Psarq_ri" -> Some (Psarq_ri (rd, imm))
        | "Prorq_ri" -> Some (Prorq_ri (rd, imm))
        | "Pshll_ri" -> Some (Pshll_ri (rd, imm))
        | "Pshrl_ri" -> Some (Pshrl_ri (rd, imm))
        | "Psarl_ri" -> Some (Psarl_ri (rd, imm))
        | "Prorl_ri" -> Some (Prorl_ri (rd, imm))
        | "Prolw_ri" -> Some (Prolw_ri (rd, imm))
        | _ -> None
        end

    | ("Pmovl_ri" | "Paddl_ri" | "Psubl_ri" | "Pandl_ri" | "Porl_ri" | "Pxorl_ri" |
        "Ptestq_ri" | "Ptestl_ri" | "Pcmpq_ri" | "Pcmpl_ri"), [r1; imm32] ->
        let* rd   = parse_ireg r1       in
        let* imm  = parse_u32_word imm32 in
        begin match opc with
        | "Pmovl_ri" -> Some (Pmovl_ri (rd, imm))
        | "Paddl_ri" -> Some (Paddl_ri (rd, imm))
        | "Psubl_ri" -> Some (Psubl_ri (rd, imm))
        | "Pandl_ri" -> Some (Pandl_ri (rd, imm))
        | "Pxorl_ri" -> Some (Pxorl_ri (rd, imm))
        | "Porl_ri" -> Some (Porl_ri (rd, imm))
        | "Ptestq_ri" -> Some (Ptestq_ri (rd, imm))
        | "Ptestl_ri" -> Some (Ptestl_ri (rd, imm))
        | "Pcmpq_ri" -> Some (Pcmpq_ri (rd, imm))
        | "Pcmpl_ri" -> Some (Pcmpl_ri (rd, imm))
        | _ -> None
        end

    | ("Pmovq_ri", [r1; imm64]) ->
        let* rd   = parse_ireg r1       in
        let* imm  = parse_u64_word imm64 in
        begin match opc with
        | "Pmovq_ri" -> Some (Pmovq_ri (rd, imm))
        | _ -> None
        end
      
    | _, [r1; r2] when
        List.mem opc
         ["Paddq_rr"; "Psubq_rr"; "Pandq_rr"; "Porq_rr"; "Pxorq_rr";
          "Paddl_rr"; "Psubl_rr"; "Pandl_rr"; "Porl_rr"; "Pxorl_rr";
          "Pmovq_rr"; "Ptestq_rr"; "Pxchgq_rr"; "Pcmpq_rr"; "Pcmpl_rr"; 
          "Pmovl_rr"; "Ptestl_rr"; "Pmovsl_rr"] ->
        let* rd = parse_ireg r1 in
        let* rs = parse_ireg r2 in
        begin match opc with
        | "Paddq_rr" -> Some (Paddq_rr (rd, rs))
        | "Psubq_rr" -> Some (Psubq_rr (rd, rs))
        | "Porq_rr"  -> Some (Porq_rr  (rd, rs))
        | "Pandq_rr" -> Some (Pandq_rr (rd, rs))
        | "Pxorq_rr" -> Some (Pxorq_rr (rd, rs))
        | "Pmovq_rr" -> Some (Pmovq_rr (rd, rs))
        | "Pxchgq_rr"-> Some (Pxchgq_rr(rd, rs))
        | "Pmovsl_rr"-> Some (Pmovsl_rr(rd, rs))
        | "Paddl_rr" -> Some (Paddl_rr (rd, rs))
        | "Psubl_rr" -> Some (Psubl_rr (rd, rs))
        | "Porl_rr"  -> Some (Porl_rr  (rd, rs))
        | "Pandl_rr" -> Some (Pandl_rr (rd, rs))
        | "Pxorl_rr" -> Some (Pxorl_rr (rd, rs))
        | "Pmovl_rr" -> Some (Pmovl_rr (rd, rs))
        | "Ptestq_rr"-> Some (Ptestq_rr(rd, rs))
        | "Ptestl_rr"-> Some (Ptestl_rr(rd, rs))
        | "Pcmpq_rr"-> Some (Pcmpq_rr(rd, rs))
        | "Pcmpl_rr"-> Some (Pcmpl_rr(rd, rs))
        | _ -> None
        end

    | _, [r1] when
        List.mem opc
          ["Pmulq_r";"Pimulq_r";"Pmull_r";"Pimull_r";
           "Pdivq_r";"Pdivl_r";"Pidivq_r";"Pidivl_r";
           "Pshlq_r";"Pshll_r";"Pshrq_r";"Pshrl_r";
           "Psarq_r";"Psarl_r";"Pnegq";"Pnegl";
           "Pbswapq";"Pbswapl"] ->
        let* rd = parse_ireg r1 in
        begin match opc with
        | "Pmulq_r"  -> Some (Pmulq_r  rd)
        | "Pimulq_r" -> Some (Pimulq_r rd)
        | "Pmull_r"  -> Some (Pmull_r  rd)
        | "Pimull_r" -> Some (Pimull_r rd)
        | "Pdivq_r"  -> Some (Pdivq_r  rd)
        | "Pdivl_r"  -> Some (Pdivl_r  rd)
        | "Pidivq_r"  -> Some (Pidivq_r  rd)
        | "Pidivl_r"  -> Some (Pidivl_r  rd)
        | "Pshlq_r"  -> Some (Pshlq_r  rd)
        | "Pshrq_r"  -> Some (Pshrq_r  rd)
        | "Psarq_r"  -> Some (Psarq_r  rd)
        | "Pshll_r"  -> Some (Pshll_r  rd)
        | "Pshrl_r"  -> Some (Pshrl_r  rd)
        | "Psarl_r"  -> Some (Psarl_r  rd)
        | "Pnegq"    -> Some (Pnegq    rd)
        | "Pnegl"    -> Some (Pnegl    rd)
        | "Pbswapq"  -> Some (Pbswapq  rd)
        | "Pbswapl"  -> Some (Pbswapl  rd)
        | _ -> None
        end

    | _ -> None
    end

let exec_x64_encode () =

  let ic = open_in "../0-data/step1.in" in
  let oc = open_out "../0-data/step2.in" in

  try
  while true do

    let line = input_line ic in

    let line = String.trim line in
    if line <> "" then (
      match parse_instruction line with
        | None ->
            Printf.eprintf "Warning: cannot parse line: %s\n%!" line
        | Some ins -> begin
            Printf.fprintf oc "%s\n" line;

            match x64_encode ins with
            | None ->
                Printf.eprintf "Encode failed: %s\n%!" line
            | Some bytes ->
                List.iter
                  (fun w -> Printf.fprintf oc "%Ld " (myint_to_int64 (the_int
                    (len_bit0 (len_bit0 (len_bit0 len_num1))) w))
                  )
                  bytes;
                output_char oc '\n'
                  end 
      (*output_string oc line;
      output_char oc '\n'*)
    )
  done
with
| End_of_file -> 
    close_in ic;
    close_out oc;
    Printf.printf "File copy completed. Results written to ../0-data/step2.in\n"
| exn -> 
    close_in ic;
    close_out oc;
    Printf.eprintf "An error occurred: %s\n" (Printexc.to_string exn);
    raise exn

let () = exec_x64_encode ()

end;; (*struct x64_encode*)
