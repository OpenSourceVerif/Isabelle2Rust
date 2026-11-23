use isabelle_exported::SignatureResultGraph::{
    even_length, odd_length, witness_branch, Itself, List,
};
use std::marker::PhantomData;

fn bool_list(length: usize, seed: bool) -> List<bool> {
    (0..length).fold(List::Nil, |xs, i| {
        List::Cons(seed ^ (i % 2 == 0), Box::new(xs))
    })
}

#[test]
fn mutual_recursion_keeps_its_boolean_result() {
    for length in 0..65 {
        for seed in [false, true] {
            assert_eq!(even_length(bool_list(length, seed)), length % 2 == 0);
            assert_eq!(odd_length(bool_list(length, seed)), length % 2 != 0);
        }
    }
}

#[test]
fn both_branch_equations_keep_the_witness_type() {
    for b in [false, true] {
        let _: Itself<bool> = witness_branch(b, Itself::Type(PhantomData));
        let _: Itself<Vec<bool>> = witness_branch(b, Itself::Type(PhantomData));
    }
}
