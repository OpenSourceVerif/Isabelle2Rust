theory ArithmeticDashu_Test
  imports "Rust.Rust_Dashu_Setup"
begin

definition generic_sub :: "'a::minus \<Rightarrow> 'a \<Rightarrow> 'a" where
  "generic_sub x y = x - y"

definition check_sub :: bool where
  "check_sub = (generic_sub (1 :: nat) 2 = 0 \<and> generic_sub (1 :: int) 2 = -1)"

definition check_div_mod :: bool where
  "check_div_mod = (let x = (-17 :: int) in
    x div 5 = -4 \<and> x mod 5 = 3 \<and> 17 div (-5 :: int) = -4 \<and>
    17 mod (-5 :: int) = -3 \<and> x div 0 = 0 \<and> x mod 0 = x)"

definition check_large :: bool where
  "check_large = (let n = (2^160 :: nat) in
    integer_of_nat n = 1461501637330902918203684832716283019655932542976 \<and>
    nat_of_integer (integer_of_nat n + 1) = n + 1)"

definition dictionary_ops :: "'a::{zero,one,plus,minus,times,divide,modulo,equal,ord} => 'a => ('a * 'a * 'a * 'a * 'a * 'a * 'a * bool * bool * bool)" where
 "dictionary_ops x y = (0, 1, x + y, x - y, x * y, x div y, x mod y, x = y, x < y, x \<le> y)"
definition dictionary_signed :: "'a::{abs,uminus} => 'a * 'a" where
 "dictionary_signed x = (abs x, -x)"
definition nat_dictionary :: "nat => nat => (nat * nat * nat * nat * nat * nat * nat * bool * bool * bool)" where
 "nat_dictionary x y = dictionary_ops x y"
definition int_dictionary :: "int => int => (int * int * int * int * int * int * int * bool * bool * bool)" where
 "int_dictionary x y = dictionary_ops x y"
definition integer_dictionary :: "integer => integer => (integer * integer * integer * integer * integer * integer * integer * bool * bool * bool)" where
 "integer_dictionary x y = dictionary_ops x y"
definition int_signed :: "int => int * int" where "int_signed x = dictionary_signed x"
definition integer_signed :: "integer => integer * integer" where "integer_signed x = dictionary_signed x"

code_printing code_module Dashu_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
    use crate::ArithmeticDashu::*;
    #[test]
    fn subtraction() { assert!(check_sub()); }
    #[test]
    fn division_and_remainder() { assert!(check_div_mod()); }
    #[test]
    fn large_conversion() { assert!(check_large()); }
}
\<close>

code_printing code_module Dashu_Dictionary_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
use crate::ArithmeticDashu as code;
use dashu_int::{IBig, UBig};
#[test]
fn natural_dictionary_operations() {
 for x in 0u32..=12 { for y in 0u32..=12 {
  let (z,(o,(a,(s,(m,(d,(r,(eq,(lt,le))))))))) = code::nat_dictionary(UBig::from(x),UBig::from(y));
  assert_eq!((z,o,a,s,m,d,r,eq,lt,le),(UBig::ZERO,UBig::ONE,UBig::from(x+y),UBig::from(x.saturating_sub(y)),UBig::from(x*y),UBig::from(if y==0{0}else{x/y}),UBig::from(if y==0{x}else{x%y}),x==y,x<y,x<=y));
 }}
}
#[test]
fn signed_dictionary_operations_and_aliases() {
 for x in -12i32..=12 { for y in -12i32..=12 {
  let mut q=if y==0 {0}else{x/y}; let mut r=if y==0{x}else{x%y};
  if y!=0 && r!=0 && ((r<0)!=(y<0)) {q-=1;r+=y;}
  let expected=(IBig::ZERO,(IBig::ONE,(IBig::from(x+y),(IBig::from(x-y),(IBig::from(x*y),(IBig::from(q),(IBig::from(r),(x==y,(x<y,x<=y)))))))));
  assert_eq!(code::int_dictionary(IBig::from(x),IBig::from(y)),expected);
  assert_eq!(code::integer_dictionary(IBig::from(x),IBig::from(y)),expected);
  assert_eq!(code::int_signed(IBig::from(x)),(IBig::from(x.abs()),IBig::from(-x)));
  assert_eq!(code::integer_signed(IBig::from(x)),(IBig::from(x.abs()),IBig::from(-x)));
 }}
}
#[test]
fn arbitrary_precision_dictionary_values() {
 let big=UBig::ONE<<200usize;
 let (_,(_,(_,(_,(_, (q,(r,_)))))))=code::nat_dictionary(big.clone()+3u32,UBig::from(5u32));
 assert_eq!(q*5u32+r,big+3u32);
 let large=IBig::ONE<<200usize;
 let (_,(_,(_,(_,(_, (q,(r,_)))))))=code::integer_dictionary(-large.clone(),IBig::from(-7i32));
 assert_eq!(q*IBig::from(-7i32)+r,-large);
}
}
\<close>

export_code check_sub check_div_mod check_large nat_dictionary int_dictionary integer_dictionary int_signed integer_signed
 in Rust module_name ArithmeticDashu

end
