// The HOL observation lemmas cover both branches of the source boolean payload.
// Generic class dispatch and closure capture must both preserve that payload.
use isabelle_exported::RuntimeSizedName as code;

#[test]
fn source_sized_class_instance_preserves_its_value() {
    for value in [false, true] {
        assert_eq!(code::observe_sized(value), value);
    }
}

#[test]
fn source_clone_operation_does_not_interfere_with_capture_cloning() {
    for value in [false, true] {
        assert_eq!(code::observe_capture(value), value);
    }
}
