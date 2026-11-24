theory Mapped_Instance_Coherence_Test
 imports Rust_Base_Setup
begin
class audit_mark = fixes audit_mark :: "'a => bool"
datatype audit_left = AuditLeft bool
datatype audit_right = AuditRight bool
instantiation audit_left :: audit_mark
begin
fun audit_mark_audit_left :: "audit_left => bool" where "audit_mark_audit_left (AuditLeft x) = x"
instance ..
end
instantiation audit_right :: audit_mark
begin
fun audit_mark_audit_right :: "audit_right => bool" where "audit_mark_audit_right (AuditRight x) = (\<not>x)"
instance ..
end
definition audit_left_read :: "bool => bool" where "audit_left_read b = audit_mark (AuditLeft b)"
definition audit_right_read :: "bool => bool" where "audit_right_read b = audit_mark (AuditRight b)"
code_printing
 type_constructor audit_left \<rightharpoonup> (Rust) "bool"
| type_constructor audit_right \<rightharpoonup> (Rust) "bool"
| constant AuditLeft \<rightharpoonup> (Rust) "(_)"
| constant AuditRight \<rightharpoonup> (Rust) "(_)"
text \<open>
  The adaptations preserve each individual constructor representation, but the
  source instances implement different operations on the same Rust bool. Rust
  has one trait implementation per receiver, so this export must be rejected
  instead of redirecting both source operations to one arbitrary method.
\<close>

ML \<open>
  val result = Exn.capture (fn () =>
    Code_Target.produce_code @{context} false
      [@{const_name audit_mark}, @{const_name audit_left_read}, @{const_name audit_right_read}]
      "Rust" "MappedInstanceAudit" NONE []) ();
  val _ = (case result of
    Exn.Exn (ERROR message) =>
      if String.isSubstring "cannot merge distinct instances" message then ()
      else error message
  | Exn.Exn exn => Exn.reraise exn
  | Exn.Res _ => error "Conflicting source instances were silently merged");
\<close>

text \<open>
  The same registered native operation may safely share a receiver. This custom
  class is not a numeric built-in: its dictionary metadata and actual generated
  method, rather than its name, establish the shared implementation.
\<close>
class audit_shared = fixes audit_shared :: "'a => bool"
instantiation audit_left :: audit_shared
begin
fun audit_shared_audit_left :: "audit_left => bool" where
 "audit_shared_audit_left (AuditLeft x) = x"
instance ..
end
instantiation audit_right :: audit_shared
begin
fun audit_shared_audit_right :: "audit_right => bool" where
 "audit_shared_audit_right (AuditRight x) = x"
instance ..
end
code_printing
 constant "audit_shared :: audit_left => bool" \<rightharpoonup> (Rust) "_"
| constant "audit_shared :: audit_right => bool" \<rightharpoonup> (Rust) "_"
definition audit_native_use :: "'a::audit_shared => bool" where
 "audit_native_use x = audit_shared x"
definition audit_native_left :: "bool => bool" where
 "audit_native_left b = audit_native_use (AuditLeft b)"
definition audit_native_right :: "bool => bool" where
 "audit_native_right b = audit_native_use (AuditRight b)"
export_code audit_native_use audit_native_left audit_native_right
 in Rust module_name MappedInstanceCoherence
end
