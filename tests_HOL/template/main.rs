#![feature(box_patterns)]
mod Arith;
mod GCD;
mod Product_Type;
mod Hol_Test_Integer;
use crate::Hol_Test_Integer::gcd_test;

fn main(){
    println!("hol_test = {}", gcd_test())
}
