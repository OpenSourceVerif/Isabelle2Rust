// Copy to export1/tests/shared_instance_types.rs after generating the theory.
// The missing witness function is not invoked. Both real class instances must
// remain present even when their carrier occurs after a nested function arrow.
use isabelle_exported::SharedInstanceTypes::*;

#[test]
fn distinct_carriers_dispatch_to_their_own_methods() {
    for len in 0..=5 {
        for flag in [false, true] {
            for bit in [false, true] {
                let payload = Carrier::Carrier(vec![bit; len]);
                assert_eq!(probe_values(flag, payload.clone(), bit), flag && bit);
                assert_eq!(
                    <Carrier<Vec<bool>> as CarrierProbe>::probe_tag(flag, payload),
                    flag
                );
                assert_eq!(<bool as CarrierProbe>::probe_tag(flag, bit), flag && bit);
            }
        }
    }
}
