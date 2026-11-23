// Copy into export1/tests/method_call_bounds_alignment.rs after generating
// Method_Call_Bounds_Alignment_Test. The first payload is deliberately not an
// inhabitant of the generated Equal trait; only the second field is compared.
// The absent unused_pair_copy operation is never invoked.
use isabelle_exported::MethodCallBoundsAlignment::*;

#[test]
fn opaque_first_fields_do_not_affect_comparison() {
    for p in [false, true] {
        for q in [false, true] {
            for x in [false, true] {
                for y in [false, true] {
                    assert_eq!(compare_opaque(p, x, q, y), x == y);
                }
            }
        }
    }
}

#[test]
fn generic_calls_require_only_the_second_dictionary() {
    for len in 0..=5 {
        for x in [false, true] {
            for y in [false, true] {
                let left = PayloadPair::PayloadPair(vec![true; len], x);
                let right = PayloadPair::PayloadPair(vec![false; 5 - len], y);
                assert_eq!(compare_payloads(left.clone(), right.clone()), x == y);
                assert_eq!(
                    <PayloadPair<Vec<bool>, bool> as PairCompare>::pair_compare(left, right),
                    x == y
                );
            }
        }
    }
}
