use isabelle_exported::MappedArithmetic as code;
use num_bigint::BigInt;

fn check_arithmetic(x: BigInt, y: BigInt, n: u32) {
    let expected = (
        BigInt::ZERO,
        (x.clone() + y.clone() + x.clone(),
         (x.clone() * y.clone(), (x.pow(n), BigInt::from(37)))),
    );
    assert_eq!(code::arithmetic_result(x, y, BigInt::from(n)), expected);
}

#[test]
fn native_dictionary_operations_cover_zero_and_small_values() {
    for x in 0..6 {
        for y in 0..6 {
            for n in 0..5 {
                check_arithmetic(BigInt::from(x), BigInt::from(y), n);
            }
        }
    }
}

#[test]
fn native_dictionary_operations_preserve_arbitrary_precision() {
    let huge = BigInt::from(1u8) << 200usize;
    for n in 0..4 {
        check_arithmetic(huge.clone(), huge.clone() + 1u8, n);
    }
}
