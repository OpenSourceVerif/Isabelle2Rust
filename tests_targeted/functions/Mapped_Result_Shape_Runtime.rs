use isabelle_exported::MappedResultShape::*;
use std::rc::Rc;

fn callback(table: u8) -> Rc<dyn Fn(bool, bool) -> bool> {
    Rc::new(move |x, y| table & (1 << (usize::from(x) * 2 + usize::from(y))) != 0)
}

#[test]
fn mapped_results_retain_context_and_plain_controls() {
    for left in 0u8..16 {
        for right in 0u8..16 {
            assert_eq!(equal_mapped_pair(callback(left), callback(right)), left == right);
        }
        for bit in [false, true] {
            assert_eq!(observe_plain_mapped_pair(callback(left), bit), callback(left)(bit, bit));
        }
    }
}
