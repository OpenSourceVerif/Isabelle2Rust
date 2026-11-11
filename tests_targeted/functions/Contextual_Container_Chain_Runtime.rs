use isabelle_exported::ContextualContainerChain::{
    chain_deep_8, chain_deep_32, chain_intersection, chain_plain, chain_product, List, Set,
};
use std::rc::Rc;

type Callback = Rc<dyn Fn(bool, bool) -> bool>;

fn relation(entries: &[(bool, u8)]) -> Set<(bool, Callback)> {
    let mut list = List::Nil;
    for &(key, mask) in entries.iter().rev() {
        let function: Callback = Rc::new(move |x, y| mask & (1 << (2 * x as u8 + y as u8)) != 0);
        list = List::Cons((key, function), Box::new(list));
    }
    Set::Set(list)
}

fn contains(set: Set<bool>, expected: bool) -> bool {
    let (mut list, complement) = match set {
        Set::Set(list) => (list, false),
        Set::Coset(list) => (list, true),
    };
    let mut found = false;
    while let List::Cons(value, tail) = list {
        found |= value == expected;
        list = *tail;
    }
    found != complement
}

fn check_observation(entries: &[(bool, u8)], observe: fn(Set<(bool, Callback)>) -> Set<bool>) {
    for value in [false, true] {
        let expected = entries.iter().any(|&(key, mask)| (key == (mask & 4 != 0)) == value);
        assert_eq!(contains(observe(relation(entries)), value), expected);
    }
}

#[test]
fn empty_inputs_stay_empty() {
    for observe in [chain_plain, chain_intersection, chain_product, chain_deep_8, chain_deep_32] {
        assert!(!contains(observe(relation(&[])), false));
        assert!(!contains(observe(relation(&[])), true));
    }
}

#[test]
fn every_binary_boolean_function_keeps_its_observation() {
    for mask in 0..16 {
        for key in [false, true] {
            for observe in [chain_plain, chain_intersection] {
                check_observation(&[(key, mask)], observe);
            }
        }
    }
}

#[test]
fn product_uses_the_existing_source_map() {
    for mask in 0..16 {
        for key in [false, true] {
            assert!(contains(chain_product(relation(&[(key, mask)])), false));
            assert!(contains(chain_product(relation(&[(key, mask)])), true));
        }
    }
}

#[test]
fn longer_call_chains_keep_the_same_container_layout() {
    let entries: Vec<_> = (0..16).map(|mask| (mask % 2 == 0, mask)).collect();
    for observe in [chain_deep_8, chain_deep_32] {
        for entry in &entries {
            check_observation(&[*entry], observe);
        }
        check_observation(&entries, observe);
    }
}
