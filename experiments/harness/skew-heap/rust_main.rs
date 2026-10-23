#![forbid(unsafe_code)]
use num_bigint::BigInt;
use std::io::{self, BufRead};

#[cfg(feature = "candidate")]
mod candidate;
#[cfg(feature = "candidate")]
use candidate::{Tree, merge};
#[cfg(not(feature = "candidate"))]
use exported::Reference::{Tree, merge};

#[cfg(feature = "candidate")]
type Value = BigInt;
#[cfg(not(feature = "candidate"))]
#[derive(Clone)]
struct Value(BigInt);
#[cfg(not(feature = "candidate"))]
impl std::str::FromStr for Value {
    type Err = num_bigint::ParseBigIntError;
    fn from_str(s: &str) -> Result<Self, Self::Err> { s.parse().map(Value) }
}
#[cfg(not(feature = "candidate"))]
impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { self.0.fmt(f) }
}
#[cfg(not(feature = "candidate"))]
impl exported::Reference::Ord for Value {
    fn less_eq(a: Self, b: Self) -> bool { a.0 <= b.0 }
    fn less(a: Self, b: Self) -> bool { a.0 < b.0 }
}

fn parse(tokens: &mut std::str::SplitWhitespace<'_>) -> Tree<Value> {
    match tokens.next().expect("tree token") {
        "#" => Tree::Leaf,
        token => {
            let value = token.parse().expect("integer");
            let left = parse(tokens);
            let right = parse(tokens);
            Tree::Node(Box::new(left), value, Box::new(right))
        }
    }
}

fn encode(tree: &Tree<Value>, out: &mut Vec<String>) {
    match tree {
        Tree::Leaf => out.push("#".into()),
        Tree::Node(left, value, right) => {
            out.push(value.to_string());
            encode(left, out);
            encode(right, out);
        }
    }
}

fn main() {
    for line in io::stdin().lock().lines() {
        let line = line.expect("stdin");
        let mut tokens = line.split_whitespace();
        let a = parse(&mut tokens);
        let b = parse(&mut tokens);
        assert!(tokens.next().is_none());
        let merged = merge(a, b);
        let mut output = Vec::new();
        encode(&merged, &mut output);
        println!("{}", output.join(" "));
    }
}
