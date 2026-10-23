use num_bigint::BigInt;
use std::io::{self, BufRead};

#[cfg(feature = "candidate")]
mod candidate;

#[cfg(not(feature = "candidate"))]
use exported::Reference::{Equal, List, last_index};

#[cfg(not(feature = "candidate"))]
#[derive(Clone)]
struct Value(BigInt);

#[cfg(not(feature = "candidate"))]
impl Equal for Value {
    fn equal(a: Self, b: Self) -> bool { a.0 == b.0 }
}

fn evaluate(xs: Vec<BigInt>, x: BigInt) -> BigInt {
    #[cfg(feature = "candidate")]
    { candidate::last_index(&xs, &x) }
    #[cfg(not(feature = "candidate"))]
    {
        let list = xs.into_iter().rev().fold(List::Nil, |tail, value|
            List::Cons(Value(value), Box::new(tail)));
        #[cfg(feature = "stage2")]
        { last_index(&list, Value(x)) }
        #[cfg(not(feature = "stage2"))]
        { last_index(list, Value(x)) }
    }
}

fn main() {
    for line in io::stdin().lock().lines() {
        let line = line.expect("stdin");
        let mut fields = line.split_whitespace();
        let x = fields.next().expect("query").parse::<BigInt>().expect("integer");
        let xs = fields.map(|s| s.parse::<BigInt>().expect("integer")).collect();
        println!("{}", evaluate(xs, x));
    }
}
