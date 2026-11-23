// Copy to AFP_Integer_Equations_Test/export1/tests/afp_integer.rs after make gen.
// BigInt::pow and primitive ilog2 provide independent oracles. Large exponents
// with bases 0 and +/-1 detect narrowing while keeping the result inexpensive.
use isabelle_exported::AFPInteger as code;
use num_bigint::BigInt;

#[test]
fn powers_preserve_signed_bases_and_negative_exponent_truncation() {
    for a in -12i32..=12 {
        for n in -4i32..=24 {
            let expected = BigInt::from(a).pow(n.max(0) as u32);
            assert_eq!(code::power_integer(BigInt::from(a), BigInt::from(n)), expected);
        }
    }
}

#[test]
fn logarithms_are_total_and_match_magnitude_bit_boundaries() {
    for a in -4096i32..=4096 {
        let magnitude = a.unsigned_abs();
        let expected = if magnitude == 0 { 0 } else { magnitude.ilog2() };
        assert_eq!(code::log2_integer(BigInt::from(a)), BigInt::from(expected));
    }
    for bits in [127u32, 128, 255, 512, 2048] {
        let boundary = BigInt::from(1u8) << bits;
        for delta in [-1i32, 0, 1] {
            let magnitude = &boundary + delta;
            let expected = BigInt::from(if delta < 0 { bits - 1 } else { bits });
            for value in [magnitude.clone(), -magnitude] {
                assert_eq!(code::log2_integer(value), expected);
            }
        }
    }
}

#[test]
fn large_values_and_exponents_keep_all_bits() {
    let huge = BigInt::from(1u8) << 130u32;
    for (exponent, odd) in [(huge.clone(), false), (&huge + 1u8, true)] {
        assert_eq!(code::power_integer(BigInt::from(-1i8), exponent.clone()),
                   BigInt::from(if odd { -1i8 } else { 1 }));
        assert_eq!(code::power_integer(BigInt::from(1u8), exponent.clone()), BigInt::from(1u8));
        assert_eq!(code::power_integer(BigInt::from(0u8), exponent), BigInt::from(0u8));
    }
    assert_eq!(code::power_integer(BigInt::from(0u8), -huge), BigInt::from(1u8));
    assert_eq!(code::power_integer(BigInt::from(2u8), BigInt::from(2048u32)),
               BigInt::from(1u8) << 2048u32);
    assert_eq!(code::afp_integer_observations(BigInt::from(-8i8), BigInt::from(3u8)),
               (BigInt::from(-512i32), BigInt::from(3u8)));
}
