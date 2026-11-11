use isabelle_exported::ContextualResultParameter as code;
use std::rc::Rc;

#[test]
fn result_only_parameters_keep_the_dictionary_selected_representation() {
    assert!(code::contextual_empty());
    for b in [false, true] {
        assert!(code::contextual_after(b));
        assert!(code::contextual_pair(b));
    }
}

#[test]
fn witnessed_and_result_only_parameters_use_consistent_shapes() {
    for bits in 0u8..16 {
        let f: Rc<dyn Fn(bool, bool) -> bool> =
            Rc::new(move |x, y| bits & (1 << ((x as u8) * 2 + y as u8)) != 0);
        for _ in 0..3 {
            assert_eq!(code::contextual_marked(f.clone()), bits == 8);
        }
    }
}

#[test]
fn ordinary_generic_instantiation_retains_its_values() {
    for b in [false, true] {
        assert_eq!(code::ordinary_marker(b), b);
    }
}
