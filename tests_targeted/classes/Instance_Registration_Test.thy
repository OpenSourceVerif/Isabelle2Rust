theory Instance_Registration_Test
 imports Rust_Base_Setup
begin
class audit_probe = fixes audit_probe :: "'a => bool"
datatype audit_carrier = AuditCarrier bool
definition audit_generic :: "'a::audit_probe => bool" where "audit_generic x = audit_probe x"
setup \<open>Sign.add_path "audit_probe_audit_carrier_inst"\<close>
definition audit_probe_audit_carrier :: "audit_carrier => audit_carrier" where "audit_probe_audit_carrier x = x"
setup \<open>Sign.parent_path\<close>
definition audit_identity_observation :: "bool => bool" where
 "audit_identity_observation b =
   (case audit_probe_audit_carrier_inst.audit_probe_audit_carrier (AuditCarrier b) of
      AuditCarrier c => c)"

export_code audit_identity_observation audit_generic audit_probe_audit_carrier_inst.audit_probe_audit_carrier in Rust module_name InstanceFallbackAudit
end
