// Copy to AFP_Divmod_Checked128_Test/export1/tests/afp_divmod.rs after make gen.
// Paired division must retain the selected primitive's full input range.
// In particular MIN / 1 and natural MAX / 1 have representable results; neither
// may overflow by taking abs MIN or converting natural MAX into signed i128.
use isabelle_exported::AFPDivmod as code;

#[test]
fn signed_small_values_match_floor_division() {
    for a in -32i128..=32 {
        for b in -32i128..=32 {
            let expected = if b == 0 { (0, a) } else {
                let q = ((a as f64) / (b as f64)).floor() as i128;
                (q, a - q * b)
            };
            assert_eq!(code::afp_signed_divmod(a, b), expected);
        }
    }
}

#[test]
fn full_signed_boundaries_preserve_representable_results() {
    for (a, b, expected) in [
        (i128::MIN, 1, (i128::MIN, 0)),
        (i128::MIN, 2, (i128::MIN / 2, 0)),
        (i128::MIN, i128::MIN, (1, 0)),
        (i128::MIN, 0, (0, i128::MIN)),
        (1, i128::MIN, (-1, i128::MIN + 1)),
        (-1, i128::MIN, (0, -1)),
        (i128::MAX, -1, (-i128::MAX, 0)),
    ] {
        assert_eq!(code::afp_signed_divmod(a, b), expected);
    }
    assert!(std::panic::catch_unwind(|| code::afp_signed_divmod(i128::MIN, -1)).is_err());
}

#[test]
fn natural_division_retains_the_full_unsigned_range() {
    for a in [0, 1, i128::MAX as u128, 1u128 << 127, u128::MAX] {
        for b in [0, 1, 2, 1u128 << 127, u128::MAX] {
            let expected = if b == 0 { (0, a) } else { (a / b, a % b) };
            assert_eq!(code::afp_natural_divmod(a, b), expected);
        }
    }
}

#[test]
fn guarded_helper_retains_its_nonnegative_domain() {
    assert_eq!(code::afp_guarded_divmod(i128::MAX, 0), (0, i128::MAX));
    assert_eq!(code::afp_guarded_divmod(i128::MAX, 2), (i128::MAX / 2, 1));
    for (a, b) in [(-1, 1), (1, -1), (i128::MIN, 0)] {
        assert!(std::panic::catch_unwind(|| code::afp_guarded_divmod(a, b)).is_err());
    }
}
