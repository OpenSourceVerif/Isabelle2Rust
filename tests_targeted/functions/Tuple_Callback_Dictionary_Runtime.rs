// Compare generated evaluation with the HOL observation lemmas. Every root
// invokes the callback and the recursively unary type-class dictionary.
// Tuple, nominal-constructor and nested boxed-list patterns must agree.
use isabelle_exported::TupleCallbackDictionary as code;
use std::rc::Rc;

#[test]
fn callback_patterns_and_dictionary_observe_the_same_function() {
    let observers: [fn(Rc<dyn Fn(bool, bool) -> bool>) -> bool; 3] = [
        code::observe_tuple_callback,
        code::observe_box_callback,
        code::observe_list_callback,
    ];
    for observe in observers {
        assert!(observe(Rc::new(|x: bool, _y: bool| !x)));
        assert!(!observe(Rc::new(|_x: bool, y: bool| y)));
        assert!(!observe(Rc::new(|_x: bool, y: bool| !y)));
    }
}
