use isabelle_exported::MappedInstanceCoherence as code;
#[test]
fn identical_registered_methods_share_one_impl() {
    for value in [false, true] {
        assert_eq!(code::audit_native_left(value), value);
        assert_eq!(code::audit_native_right(value), value);
    }
}
