#![feature(box_patterns)]
mod Arith;
mod GCD;
mod Product_Type;
mod Code_Test_Rust;
use crate::Code_Test_Rust::gcd_test;

fn main(){
    println!("hol_test = {}", gcd_test())
}
