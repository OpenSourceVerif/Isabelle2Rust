use isabelle_exported::CaseFunctionArity::*;
use std::cell::Cell;
use std::rc::Rc;

#[test]
fn case_results_preserve_partial_and_full_applications() {
    for table in 0u8..16 {
        let callback: Rc<dyn Fn(bool, bool) -> bool> = Rc::new(move |a, b| {
            table & (1 << (usize::from(a) * 2 + usize::from(b))) != 0
        });
        for a in [false, true] {
            let Option::Some(partial) = partial_case_callback(ArityCallback::ArityCallback(callback.clone()), a)
                else { panic!("missing callback") };
            let Option::Some(selected) = option_case_callback(Option::Some(callback.clone()), a)
                else { panic!("missing callback") };
            let Option::Some(default) = option_case_callback(Option::None, a)
                else { panic!("missing callback") };
            for b in [false, true] {
                assert_eq!(partial(b), callback(a, b));
                assert_eq!(selected(b), callback(a, b));
                assert_eq!(default(b), a && b);
                assert_eq!(full_case_callback(ArityCallback::ArityCallback(callback.clone()), a, b), callback(a, b));
            }
        }
    }
}

#[test]
fn partial_case_does_not_invoke_the_callback_until_called() {
    let calls = Rc::new(Cell::new(0));
    let captured = calls.clone();
    let callback: Rc<dyn Fn(bool, bool) -> bool> = Rc::new(move |a, b| {
        captured.set(captured.get() + 1);
        a != b
    });
    let Option::Some(partial) = partial_case_callback(ArityCallback::ArityCallback(callback), true)
        else { panic!("missing callback") };
    assert_eq!(calls.get(), 0);
    assert!(partial(false));
    assert!(!partial(true));
    assert_eq!(calls.get(), 2);
}
