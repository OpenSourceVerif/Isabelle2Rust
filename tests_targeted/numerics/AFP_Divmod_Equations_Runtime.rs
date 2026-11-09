// Copy to AFP_Divmod_Equations_Test/export1/tests/afp_divmod.rs after make gen.
// The signed tests characterize HOL floor division by its defining identity
// and the divisor-signed remainder interval, without duplicating AFP's sign
// case analysis. Direct calls outside the helper's specified domain must abort.
use isabelle_exported::AFPDivmod as code;
use num_bigint::BigInt;

fn check_signed(a: BigInt, b: BigInt) {
    let (q, r) = code::afp_signed_divmod(a.clone(), b.clone());
    if b == BigInt::from(0) {
        assert_eq!((q, r), (BigInt::from(0), a));
    } else {
        assert_eq!(&q * &b + &r, a);
        if b > BigInt::from(0) {
            assert!(BigInt::from(0) <= r && r < b);
        } else {
            assert!(b < r && r <= BigInt::from(0));
        }
    }
}

#[test]
fn signed_division_has_the_unique_floor_quotient_and_remainder() {
    for a in -32i32..=32 {
        for b in -32i32..=32 {
            check_signed(a.into(), b.into());
        }
    }
    let large: BigInt = (BigInt::from(1) << 260u32) + 123;
    let divisor: BigInt = (BigInt::from(1) << 130u32) + 7;
    for a in [large.clone(), -large] {
        for b in [divisor.clone(), -divisor.clone(), BigInt::from(0)] {
            check_signed(a.clone(), b);
        }
    }
}

#[test]
fn guarded_and_natural_division_keep_zero_and_large_values() {
    for a in 0u32..=64 {
        for b in 0u32..=64 {
            let expected = if b == 0 { (0, a) } else { (a / b, a % b) };
            let expected = (BigInt::from(expected.0), BigInt::from(expected.1));
            assert_eq!(code::afp_guarded_divmod(a.into(), b.into()), expected);
            assert_eq!(code::afp_natural_divmod(a.into(), b.into()), expected);
        }
    }
    let large: BigInt = (BigInt::from(1) << 260u32) + 123;
    for divisor in [BigInt::from(0), BigInt::from(1), BigInt::from(2), large.clone()] {
        let signed = code::afp_signed_divmod(large.clone(), divisor.clone());
        assert_eq!(code::afp_guarded_divmod(large.clone(), divisor.clone()), signed);
        assert_eq!(code::afp_natural_divmod(large.clone(), divisor), signed);
    }
}

#[test]
fn unspecified_helper_inputs_abort_without_evaluating_the_fallback() {
    for (a, b) in [(-1, 1), (1, -1), (-1, -1), (-1, 0)] {
        let err = std::panic::catch_unwind(|| code::afp_guarded_divmod(a.into(), b.into()))
            .expect_err("negative helper input must not be assigned a value");
        let msg = err.downcast_ref::<String>().map(String::as_str)
            .or_else(|| err.downcast_ref::<&str>().copied()).unwrap_or("");
        assert!(msg.contains("divmod_abs requires nonnegative arguments"));
    }
}
