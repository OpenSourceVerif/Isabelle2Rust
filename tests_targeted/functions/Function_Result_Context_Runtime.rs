use isabelle_exported::FunctionResultContext::*;
use std::rc::Rc;

type Callback = Rc<dyn Fn(bool, bool) -> bool>;

fn check(set: Set<Callback>, expected_bit: std::option::Option<bool>) {
    let Set::Set(mut values) = set else { panic!("unexpected complement") };
    let mut masks = Vec::new();
    while let List::Cons(f, rest) = values {
        let mut mask = 0u8;
        for a in [false, true] {
            for b in [false, true] {
                if f(a, b) { mask |= 1 << (usize::from(a) * 2 + usize::from(b)); }
            }
        }
        masks.push(mask);
        values = *rest;
    }
    masks.sort_unstable();
    let expected: Vec<_> = (0u8..16).filter(|mask|
        expected_bit.is_some_and(|bit| (mask & 1 != 0) == bit)).collect();
    assert_eq!(masks, expected);
}

#[test]
fn function_and_closure_signatures_preserve_all_callback_values() {
    for bit in [false, true] {
        check(context_conditional(bit), Some(bit));
        check(context_case(Option::Some(bit)), Some(bit));
        check(context_delayed(bit)(Unit::Unity), Some(bit));
        check(context_trait(bit), Some(bit));
        check(context_equations(List::Cons(bit, Box::new(List::Nil))), Some(bit));
        check(context_staged(List::Cons(Option::Some(bit), Box::new(List::Nil))), Some(bit));
    }
    check(context_case(Option::None), Some(true));
    check(context_equations(List::Nil), None);
    check(context_staged(List::Cons(Option::None, Box::new(List::Nil))), None);
}
