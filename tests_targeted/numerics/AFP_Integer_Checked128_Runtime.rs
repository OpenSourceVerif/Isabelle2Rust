// Copy to AFP_Integer_Checked128_Test/export1/tests/afp_integer.rs after make gen.
// Test the same proved equations in the bounded profile, including i128::MIN:
// its logarithm and first power are representable and must not take abs MIN or
// square MIN as an intermediate. Actual out-of-range powers must still fail.
use isabelle_exported::AFPInteger as code;

#[test]
fn small_powers_and_total_logarithms_match_primitive_oracles() {
    for a in -12i128..=12 {
        for n in -4i128..=24 {
            assert_eq!(code::power_integer(a, n), a.pow(n.max(0) as u32));
        }
    }
    for a in -4096i128..=4096 {
        let magnitude = a.unsigned_abs();
        let expected = if magnitude == 0 { 0 } else { magnitude.ilog2() as i128 };
        assert_eq!(code::log2_integer(a), expected);
    }
}

#[test]
fn representable_boundary_results_do_not_overflow_intermediates() {
    assert_eq!(code::log2_integer(i128::MIN), 127);
    assert_eq!(code::log2_integer(i128::MAX), 126);
    assert_eq!(code::power_integer(i128::MIN, 1), i128::MIN);
    assert_eq!(code::power_integer(i128::MIN, 0), 1);
    assert_eq!(code::power_integer(i128::MIN, i128::MIN), 1);
    assert_eq!(code::power_integer(-2, 127), i128::MIN);
    assert_eq!(code::power_integer(-1, i128::MAX), -1);
    assert_eq!(code::power_integer(-1, i128::MAX - 1), 1);
    assert_eq!(code::afp_integer_observations(-8, 3), (-512, 3));
}

#[test]
fn out_of_range_results_keep_checked_profile_behavior() {
    assert!(std::panic::catch_unwind(|| code::power_integer(2, 127)).is_err());
    assert!(std::panic::catch_unwind(|| code::power_integer(i128::MAX, 2)).is_err());
}
