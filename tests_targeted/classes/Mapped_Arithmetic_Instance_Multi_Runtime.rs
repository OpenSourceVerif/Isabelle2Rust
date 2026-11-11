use isabelle_exported::Mapped_Arithmetic_Instance_Test as code;
use num_bigint::BigInt;

#[test]
fn primitive_impls_support_generic_arithmetic_across_modules() {
    let signed = (BigInt::ZERO, (BigInt::from(-4),
        (BigInt::from(-6), (BigInt::from(9), BigInt::from(37)))));
    assert_eq!(code::integer_arithmetic(BigInt::from(-3), BigInt::from(2), BigInt::from(2)), signed);
    assert_eq!(code::int_arithmetic(BigInt::from(-3), BigInt::from(2), BigInt::from(2)), signed);
    assert_eq!(code::nat_arithmetic(BigInt::from(3), BigInt::from(2), BigInt::from(3)),
        (BigInt::ZERO, (BigInt::from(8), (BigInt::from(6), (BigInt::from(27), BigInt::from(37))))));
}
