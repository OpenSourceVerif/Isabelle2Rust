use isabelle_exported::CaseResultShape as code;
use std::rc::Rc;

fn callback(bits: u8) -> Rc<dyn Fn(bool, bool) -> bool> {
    Rc::new(move |a, b| bits & (1 << ((a as u8) * 2 + b as u8)) != 0)
}

fn check(observe: fn(Rc<dyn Fn(bool, bool) -> bool>, bool) -> bool) {
    for bits in 0..16 {
        let f = callback(bits);
        for flag in [false, true] {
            for _ in 0..3 {
                assert_eq!(observe(f.clone(), flag), (bits & 1 != 0) == flag);
            }
        }
    }
}

#[test]
fn tuple_match_preserves_the_selected_result() {
    check(code::observe_case_binding);
}

#[test]
fn ordinary_match_preserves_the_selected_result() {
    check(code::observe_case_option);
}

#[test]
fn nested_box_match_preserves_the_selected_result() {
    check(code::observe_case_nested);
}

#[test]
fn irrefutable_binding_preserves_the_selected_result() {
    check(code::observe_case_box);
}
