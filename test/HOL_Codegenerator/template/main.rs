mod Arith;
mod GCD;
mod Product_Type;
mod Code_Test_Rust;
use crate::Code_Test_Rust::gcd_test;

fn main(){
    assert!(gcd_test(), "generated Rust disagrees with the HOL smoke tests");
}
