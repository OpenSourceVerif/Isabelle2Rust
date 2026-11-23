// Copy to AFP_Field_Modulus_Test/export1/tests/afp_field.rs after make gen.
// Primitive remainders and repeated multiplication independently specify these
// small finite fields. Large constructed dividends detect narrowing. Domain
// failures must abort without evaluating the logical self-reference fallback.
use isabelle_exported::AFPField as code;
use num_bigint::BigInt;

#[test]
fn valid_moduli_preserve_small_and_arbitrary_precision_results() {
    for x in 0u32..=64 {
        for p in 1u32..=64 {
            assert_eq!(code::afp_modulus(x.into(), p.into()), BigInt::from(x % p));
        }
    }
    let p: BigInt = (BigInt::from(1u8) << 130u32) + 7u8;
    let q: BigInt = (BigInt::from(1u8) << 200u32) + 5u8;
    for r in [BigInt::from(0), BigInt::from(1), &p - 1u8] {
        assert_eq!(code::afp_modulus(&p * &q + &r, p.clone()), r);
    }
}

#[test]
fn finite_field_callers_use_the_real_modulus_operation() {
    for p in [2u32, 3, 5, 7, 11, 17] {
        for x in 0u32..p {
            for y in 0u32..p {
                assert_eq!(code::afp_field_product(p.into(), x.into(), y.into()),
                           BigInt::from((x * y) % p));
            }
            let mut expected = 1u32;
            for n in 0u32..=32 {
                assert_eq!(code::afp_field_power(p.into(), x.into(), n.into()),
                           BigInt::from(expected));
                expected = (expected * x) % p;
            }
        }
    }
}

#[test]
fn unspecified_inputs_abort_with_the_domain_message() {
    for (x, p) in [(-1, 2), (0, 0), (1, 0), (1, -1), (-1, -1)] {
        let err = std::panic::catch_unwind(|| code::afp_modulus(x.into(), p.into()))
            .expect_err("invalid modulus domain must not be assigned a value");
        let msg = err.downcast_ref::<String>().map(String::as_str)
            .or_else(|| err.downcast_ref::<&str>().copied()).unwrap_or("");
        assert!(msg.contains("mod_nonneg_pos requires a nonnegative dividend and positive modulus"));
    }
}
