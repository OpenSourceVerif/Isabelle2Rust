use isabelle_exported::FunctionValueContainerResult::{
    delayed_selected, forwarded_selected, inspect_callbacks, inspect_callbacks_direct,
    inspect_delayed, inspect_named, inspect_named_direct, List, Set, Unit,
};
use std::rc::Rc;

fn values<A>(mut list: List<A>) -> Vec<A> {
    let mut result = Vec::new();
    while let List::Cons(value, tail) = list {
        result.push(value);
        list = *tail;
    }
    result
}

fn contains(set: Set<bool>, value: bool) -> bool {
    match set {
        Set::Set(list) => values(list).contains(&value),
        Set::Coset(list) => !values(list).contains(&value),
    }
}

#[test]
fn partial_application_preserves_callback_container_results() {
    for b in [false, true] {
        assert_eq!(values(inspect_callbacks(b)), vec![b]);
        assert_eq!(values(inspect_callbacks_direct(b)), vec![b]);
    }
}

#[test]
fn named_and_delayed_producers_preserve_observations() {
    for b in [false, true] {
        for observe in [inspect_named, inspect_named_direct, inspect_delayed] {
            assert!(contains(observe(b), false));
            assert!(contains(observe(b), true));
        }
    }
}

type Callback = Rc<dyn Fn(bool) -> Rc<dyn Fn(bool) -> bool>>;

fn check_functions(set: Set<Callback>, b: bool) {
    let callbacks = match set {
        Set::Set(list) => values(list),
        Set::Coset(_) => panic!("the finite Boolean function set must enumerate its members"),
    };
    assert_eq!(callbacks.len(), 8);
    let mut masks = Vec::new();
    for callback in callbacks {
        let mut mask = 0u8;
        for x in [false, true] {
            for y in [false, true] {
                mask |= (callback(x)(y) as u8) << (2 * x as u8 + y as u8);
            }
        }
        masks.push(mask);
    }
    masks.sort_unstable();
    masks.dedup();
    let expected: Vec<_> = (0..16).filter(|mask| (mask & 1 != 0) == b).collect();
    assert_eq!(masks, expected);
}

#[test]
fn forwarded_result_retains_all_eight_function_values() {
    for b in [false, true] {
        check_functions(forwarded_selected(b), b);
    }
}

#[test]
fn returned_closure_retains_all_eight_function_values() {
    for b in [false, true] {
        check_functions(delayed_selected(b)(Unit::Unity), b);
    }
}
