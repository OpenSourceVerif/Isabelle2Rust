use isabelle_exported::MappedDeclarationShape::*;
use std::rc::Rc;

fn callback(table: u8) -> Rc<dyn Fn(bool, bool) -> bool> {
    Rc::new(move |a, b| table & (1 << (usize::from(a) * 2 + usize::from(b))) != 0)
}

#[test]
fn declarations_preserve_reordering_and_distinct_contexts() {
    for left in 0u8..16 {
        for right in 0u8..16 {
            assert_eq!(observe_declaration_pair(callback(left), callback(right)), right & 1 != 0);
            assert_eq!(observe_declaration_swap(callback(left), callback(right)), left == right && left & 1 != 0);
            assert!(observe_mapped_constructor(callback(left), callback(right)));
        }
    }
}

#[test]
fn repeated_and_unused_variables_keep_a_single_instantiation() {
    for table in 0u8..16 {
        let expected = table & 1 != 0;
        assert_eq!(observe_declaration_same(callback(table)), expected);
        assert_eq!(observe_declaration_dup(callback(table)), expected);
        assert_eq!(observe_plain_dup(callback(table)), expected);
        for flag in [false, true] {
            assert_eq!(observe_declaration_ignore(flag, callback(table)), expected);
        }
        assert!(observe_declaration_empty(callback(table)));
    }
}
