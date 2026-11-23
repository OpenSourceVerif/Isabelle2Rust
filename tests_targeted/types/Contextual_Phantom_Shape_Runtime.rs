use isabelle_exported::ContextualPhantomShape::*;
use std::rc::Rc;

#[test]
fn phantom_shapes_preserve_independent_payloads() {
    for table in 0u8..16 {
        let callback: Rc<dyn Fn(bool, bool) -> bool> = Rc::new(move |x, y| {
            table & (1 << (usize::from(x) * 2 + usize::from(y))) != 0
        });
        assert!(observe_contextual_marker(callback.clone()));
        assert!(observe_marker_pattern(callback.clone()));
        assert!(observe_contextual_chain(callback.clone()));
        for x in [false, true] {
            for y in [false, true] {
                assert_eq!(observe_marker_payload(callback.clone(), x, y), callback(x, y));
            }
        }
    }
    let ContextualMarker::ContextualMarker(_) = default_marker();
}
