// Copy to export1/tests/shared_self_types.rs after generating the theory.
// The standard trait signature keeps Self inside Itself and permits Sized
// receivers. Both concrete and generic dispatch must preserve the witness;
// the separately emitted missing-method panic stub is never invoked.
use isabelle_exported::SharedSelfTypes::*;
use std::marker::PhantomData;

fn generic_witness<A: SelfProbe>(value: Itself<A>) -> Itself<A> {
    A::self_witness(value)
}

#[test]
fn concrete_self_signature_preserves_the_witness() {
    let value = Itself::<bool>::Type(PhantomData);
    assert!(matches!(<bool as SelfProbe>::self_witness(value), Itself::Type(_)));
}

#[test]
fn nested_self_signature_supports_generic_dispatch() {
    let value = Itself::<bool>::Type(PhantomData);
    assert!(matches!(generic_witness(value), Itself::Type(_)));
}
