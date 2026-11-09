// Copy into export1/tests/dictionary_result.rs after generating the theory.
// Check that calls of a polymorphic result follow its class-selected function
// groups without changing the boolean computation or unconstrained flat calls.
use isabelle_exported::DictionaryResult::*;
use std::rc::Rc;

#[test]
fn applied_and_returned_binary_results() {
    for b in [false, true] {
        let returned = dictionary_value(b);
        for x in [false, true] {
            for y in [false, true] {
                assert_eq!(dictionary_apply(b, x, y), b && x && y);
                assert_eq!(returned(x, y), b && (x || y));
                assert_eq!(dictionary_flat_control(b, x, y), if b { x && y } else { x || y });
            }
        }
    }
}

#[test]
fn ternary_results_consume_every_returned_group() {
    for b in [false, true] {
        for x in [false, true] {
            for y in [false, true] {
                for z in [false, true] {
                    assert_eq!(dictionary_three(b, x, y, z), b && (x != y) && z);
                }
            }
        }
    }
}

#[test]
fn higher_order_domain_is_one_argument() {
    // Enumerate all unary boolean functions independently by their truth table.
    for table in 0..4u8 {
        let f: Rc<dyn Fn(bool) -> bool> = Rc::new(move |x| table & (1 << u8::from(x)) != 0);
        for b in [false, true] {
            for x in [false, true] {
                let value = table & (1 << u8::from(x)) != 0;
                assert_eq!(dictionary_higher(b, f.clone(), x), b && value);
            }
        }
    }
}
