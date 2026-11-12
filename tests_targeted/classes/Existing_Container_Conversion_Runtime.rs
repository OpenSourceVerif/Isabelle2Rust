use isabelle_exported::ExistingContainerConversion as code;
use std::rc::Rc;

type Callback = Rc<dyn Fn(bool, bool) -> bool>;

fn callback(mask: u8) -> Callback {
    Rc::new(move |x, y| mask & (1 << (2 * x as u8 + y as u8)) != 0)
}
fn list<A>(values: impl IntoIterator<Item = A>) -> code::List<A> {
    let values: Vec<_> = values.into_iter().collect();
    values.into_iter().rev().fold(code::List::Nil, |xs, x|
        code::List::Cons(x, Box::new(xs)))
}
fn values<A>(mut xs: code::List<A>) -> Vec<A> {
    let mut result = Vec::new();
    while let code::List::Cons(x, tail) = xs {
        result.push(x);
        xs = *tail;
    }
    result
}
#[test]
fn existing_lists_preserve_all_binary_boolean_functions() {
    for a in 0..16 {
        for b in 0..16 {
            assert_eq!(code::equal_callback_lists(list([callback(a)]), list([callback(b)])), a == b);
        }
    }
    assert!(code::equal_callback_lists(list([]), list([])));
    assert!(!code::equal_callback_lists(list([]), list([callback(0)])));
}
#[test]
fn set_and_coset_constructors_are_preserved() {
    for a in 0..16 {
        for b in 0..16 {
            assert_eq!(code::equal_callback_sets(
                code::Set::Set(list([callback(a)])), code::Set::Set(list([callback(b)]))), a == b);
            assert_eq!(code::equal_callback_sets(
                code::Set::Coset(list([callback(a)])), code::Set::Coset(list([callback(b)]))), a == b);
        }
    }
}
#[test]
fn roundtrip_reaches_original_flat_fields_without_changing_observations() {
    for x in [false, true] {
        for y in [false, true] {
            let fs = list((0..16).map(callback));
            let expected: Vec<_> = (0..16).map(|m| callback(m)(x, y)).collect();
            assert_eq!(values(code::observe_roundtrip(fs, x, y)), expected);
        }
    }
    assert!(values(code::observe_roundtrip(list([]), true, false)).is_empty());
}
#[test]
fn nested_products_options_and_lists_preserve_fields() {
    for a in 0..16 {
        for b in 0..16 {
            let make = |m| (true, (list([callback(8), callback(m)]), code::Option::Some(callback(m))));
            assert_eq!(code::equal_callback_nested(make(a), make(b)), a == b);
        }
    }
    let make = || (false, (list([]), code::Option::None));
    assert!(code::equal_callback_nested(make(), make()));
}
#[test]
fn nested_recursive_datatype_conversion_keeps_shape_and_values() {
    for a in 0..16 {
        for b in 0..16 {
            let make = |m| code::CallbackTree::Fork(Box::new(list([
                code::CallbackTree::Tip(callback(8)),
                code::CallbackTree::Fork(Box::new(list([code::CallbackTree::Tip(callback(m))]))),
            ])));
            assert_eq!(code::equal_callback_trees(make(a), make(b)), a == b);
        }
    }
}

#[test]
fn function_arguments_inside_existing_containers_convert_contravariantly() {
    type Consumer = Rc<dyn Fn(Callback) -> bool>;
    let consumer = |i: u8| -> Consumer { Rc::new(move |f| f(i & 2 != 0, i & 1 != 0)) };
    for a in 0..4 {
        for b in 0..4 {
            assert_eq!(code::equal_callback_consumers(list([consumer(a)]), list([consumer(b)])), a == b);
        }
    }
}
#[test]
fn conversion_helpers_retain_generic_result_parameters() {
    for a in 0..16 {
        for b in 0..16 {
            assert_eq!(code::equal_polymorphic_callbacks(list([callback(a)]), list([callback(b)])), a == b);
        }
    }
}
#[test]
fn conversion_does_not_evaluate_callbacks() {
    use std::cell::Cell;
    let count = Rc::new(Cell::new(0));
    let counter = count.clone();
    let f: Callback = Rc::new(move |a, b| { counter.set(counter.get() + 1); a != b });
    let wrapped = code::rebox_callbacks(list([f]));
    assert_eq!(count.get(), 0);
    assert_eq!(values(code::observe_callback_box(wrapped, true, false)), vec![true]);
    assert_eq!(count.get(), 1);
}

#[test]
fn finite_nested_lists_are_not_mistaken_for_expanding_type_recursion() {
    for a in 0..16 {
        for b in 0..16 {
            let make = |m| list([list([]), list([callback(8), callback(m)])]);
            assert_eq!(code::equal_callback_matrix(make(a), make(b)), a == b);
        }
    }
}

#[test]
fn arguments_to_returned_closures_use_the_returned_signature() {
    let fs = list((0..16).map(callback));
    let expected: Vec<_> = (0..16).map(|m| callback(m)(true, false)).collect();
    assert_eq!(values(code::returned_callback_consumer(fs)), expected);
}

#[test]
fn helper_names_do_not_shadow_source_variables() {
    assert!(code::conversion_named_parameter(list([])));
    assert!(!code::conversion_named_parameter(list([callback(0)])));
}
