use isabelle_exported::InstanceFallbackAudit as code;
#[test]
fn ordinary_names_do_not_create_instances() {
    assert!(code::audit_identity_observation(true));
    assert!(!code::audit_identity_observation(false));
}
