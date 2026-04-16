#![feature(box_patterns)]
pub mod Parity;
mod Euclidean_Rings;
mod Int;
mod Num;
mod Product_Type;
mod GCD;
mod Hol_Test;
mod HOL;
use crate::Hol_Test::gcd_test;

fn main(){
    println!("hol_test = {}", gcd_test())
}
