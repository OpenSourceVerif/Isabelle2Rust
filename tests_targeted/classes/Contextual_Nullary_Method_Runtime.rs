use isabelle_exported::ContextualNullaryMethod as code;
use std::rc::Rc;

fn values<A>(mut list: code::List<A>) -> Vec<A> {
    let mut result = Vec::new();
    while let code::List::Cons(value, tail) = list {
        result.push(value);
        list = *tail;
    }
    result
}

fn contains(set: code::Set<bool>, value: bool) -> bool {
    match set {
        code::Set::Set(xs) => values(xs).contains(&value),
        code::Set::Coset(xs) => !values(xs).contains(&value),
    }
}

#[test]
fn empty_set_method_preserves_inserted_functions_and_observations() {
    let mut masks = Vec::new();
    let functions = match code::relation_choices() {
        code::Set::Set(xs) => values(xs),
        code::Set::Coset(_) => panic!("expected the two explicitly inserted functions"),
    };
    assert_eq!(functions.len(), 2);
    for f in functions {
        let again = f.clone();
        let mut mask = 0u8;
        for a in [false, true] {
            for b in [false, true] {
                let value = f(a)(b);
                assert_eq!(again(a)(b), value);
                mask |= u8::from(value) << (2 * u8::from(a) + u8::from(b));
            }
        }
        masks.push(mask);
    }
    masks.sort_unstable();
    assert_eq!(masks, vec![8, 14]);
    for a in [false, true] {
        for b in [false, true] {
            for value in [false, true] {
                assert_eq!(
                    contains(code::relation_observations(a, b), value),
                    value == (a && b) || value == (a || b),
                );
            }
        }
    }
}

#[test]
fn method_result_nested_above_self_preserves_the_selected_layout() {
    let functions = values(code::layered_callbacks());
    assert_eq!(functions.len(), 1);
    for a in [false, true] {
        for b in [false, true] {
            assert_eq!(functions[0](a)(b), a != b);
        }
    }
}

#[test]
fn function_dictionary_boundaries_survive_flat_constructor_fields() {
    for a in [false, true] {
        for b in [false, true] {
            assert!(!code::observe_bottom_box(a, b));
            assert!(!code::applied_bottom(a, b));
        }
    }
}

#[test]
fn generic_dispatch_keeps_its_original_dictionary() {
    assert!(!code::generic_bottom::<bool>());
    let f: Rc<dyn Fn(bool) -> Rc<dyn Fn(bool) -> bool>> = code::generic_bottom();
    for a in [false, true] {
        for b in [false, true] {
            assert!(!f(a)(b));
        }
    }
}
