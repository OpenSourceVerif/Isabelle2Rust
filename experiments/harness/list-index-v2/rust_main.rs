#![forbid(unsafe_code)]
use num_bigint::BigInt;
use std::io::{self, BufRead};
use std::hint::black_box;
use std::time::Instant;

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

fn bench(args: &[String]) {
    let n: usize = args[2].parse().unwrap();
    let mode = args[3].as_str();
    let iterations: usize = args[4].parse().unwrap();
    let xs: Vec<BigInt> = (0..n).map(BigInt::from).collect();
    let q = match mode { "first" => 0, "last" => n-1, "absent" => n+1, _ => panic!("mode") };
    let expected = BigInt::from(if mode == "absent" { n } else { q });
    let x = BigInt::from(q);
    for _ in 0..10 { assert_eq!(evaluate(xs.clone(), x.clone()), expected); }
    let start = Instant::now();
    let mut result = BigInt::from(0);
    for _ in 0..iterations {
        result = black_box(evaluate(black_box(xs.clone()), black_box(x.clone())));
    }
    let nanos = start.elapsed().as_nanos();
    assert_eq!(result, expected);
    println!("{} {} {}", nanos, iterations, result);
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("--bench") { return bench(&args); }
    for line in io::stdin().lock().lines() {
        let line = line.expect("stdin");
        let mut fields = line.split_whitespace();
        let x = fields.next().expect("query").parse::<BigInt>().expect("integer");
        let xs = fields.map(|s| s.parse::<BigInt>().expect("integer")).collect();
        println!("{}", evaluate(xs, x));
    }
}
