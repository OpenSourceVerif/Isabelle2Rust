use isabelle_exported::ConstructedCallbackPair as code;
use std::rc::Rc;

fn callback(bits: u8) -> Rc<dyn Fn(bool, bool) -> bool> {
    Rc::new(move |a, b| bits & (1 << ((a as u8) * 2 + b as u8)) != 0)
}

#[test]
fn generic_constructor_uses_the_dictionary_selected_input_shape() {
    for bits in 0..16 {
        let f = callback(bits);
        let expected = bits & 3 == 3;
        for _ in 0..3 {
            assert_eq!(code::observe_constructed_pair(f.clone()), expected);
            assert_eq!(code::observe_direct_constructor(f.clone()), expected);
        }
    }
}

#[test]
fn selected_shape_survives_a_generic_result_and_let_binding() {
    for bits in 0..16 {
        let f = callback(bits);
        for _ in 0..3 {
            assert_eq!(code::observe_forwarded_pair(f.clone()), bits & 3 == 3);
        }
    }
}

#[test]
fn explicit_generics_preserve_input_shape_with_an_unrelated_result_variable() {
    for bits in 0..16 {
        let f = callback(bits);
        for _ in 0..3 {
            assert_eq!(code::observe_explicit_pair(f.clone()), bits & 3 == 3);
        }
    }
}
