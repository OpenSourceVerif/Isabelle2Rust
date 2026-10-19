// Independent semantic smoke checks for AFP List-Index. Enumerate all Boolean
// lists of lengths 0..5 and compare the six exported operations to Rust Vec
// indexing/insertion/removal and simple arithmetic, for both pipeline stages.
use exported::List::List;
use exported::List_Index::*;
use num_bigint::BigInt;
use std::rc::Rc;

// The export is polymorphic and does not request a concrete HOL bool instance.
// A local Boolean carrier supplies Equal without modifying the generated crate.
#[derive(Clone, Copy, Debug, PartialEq)]
struct Flag(bool);
impl exported::HOL::Equal for Flag {
    fn equal(x: Self, y: Self) -> bool { x.0 == y.0 }
}

fn list<T: Clone + 'static>(xs: &[T]) -> List<T> {
    xs.iter().rev().fold(List::Nil, |tail, x| List::Cons(x.clone(), Box::new(tail)))
}
fn vector<T: Clone + 'static>(mut xs: List<T>) -> Vec<T> {
    let mut result = Vec::new();
    while let List::Cons(x, tail) = xs {
        result.push(x);
        xs = *tail;
    }
    result
}

// Stage 2 may borrow the numeric/list inputs whose ownership demand was removed.
// These adapters only bridge the public signatures; the Vec oracle is shared.
#[cfg(not(stage2))]
fn insert(n: &BigInt, x: Flag, xs: List<Flag>) -> List<Flag> {
    insert_nth(n.clone(), x, xs)
}
#[cfg(stage2)]
fn insert(n: &BigInt, x: Flag, xs: List<Flag>) -> List<Flag> { insert_nth(n, x, xs) }
#[cfg(not(stage2))]
fn remove(n: &BigInt, xs: List<Flag>) -> List<Flag> { remove_nth(n.clone(), xs) }
#[cfg(stage2)]
fn remove(n: &BigInt, xs: List<Flag>) -> List<Flag> { remove_nth(n, xs) }
#[cfg(not(stage2))]
fn last(xs: List<Flag>, x: Flag) -> BigInt { last_index(xs, x) }
#[cfg(stage2)]
fn last(xs: List<Flag>, x: Flag) -> BigInt { last_index(&xs, x) }
#[cfg(not(stage2))]
fn mapped(n: &BigInt, xs: List<Flag>) -> List<BigInt> {
    map_index(n.clone(), Rc::new(|i: BigInt, x: Flag| i + if x.0 { 100 } else { 0 }), xs)
}
#[cfg(stage2)]
fn mapped(n: &BigInt, xs: List<Flag>) -> List<BigInt> {
    map_index(n, Rc::new(|i: BigInt, x: Flag| i + if x.0 { 100 } else { 0 }), xs)
}

fn main() {
    let mut checks = 0;
    for length in 0..=5 {
        for bits in 0..(1 << length) {
            let xs: Vec<Flag> = (0..length).map(|i| Flag(bits & (1 << i) != 0)).collect();
            for x in [Flag(false), Flag(true)] {
                let first = xs.iter().position(|v| *v == x).unwrap_or(length);
                let final_index = xs.iter().rposition(|v| *v == x).unwrap_or(length);
                assert_eq!(index(list(&xs))(x), BigInt::from(first));
                assert_eq!(find_index(Rc::new(move |v| v == x), list(&xs)), BigInt::from(first));
                assert_eq!(last(list(&xs), x), BigInt::from(final_index));
                checks += 3;
                for position in 0..=length + 2 {
                    let n = BigInt::from(position);
                    let mut expected = xs.clone();
                    expected.insert(position.min(length), x);
                    assert_eq!(vector(insert(&n, x, list(&xs))), expected);
                    checks += 1;
                }
            }
            for position in 0..=length + 2 {
                let n = BigInt::from(position);
                let mut expected = xs.clone();
                if position < expected.len() { expected.remove(position); }
                assert_eq!(vector(remove(&n, list(&xs))), expected);
                let mapped_expected: Vec<BigInt> = xs.iter().enumerate().map(
                    |(i, x)| BigInt::from(position + i + if x.0 { 100 } else { 0 })
                ).collect();
                assert_eq!(vector(mapped(&n, list(&xs))), mapped_expected);
                checks += 2;
            }
        }
    }
    println!("{checks} independent List-Index assertions passed");
}
