use isabelle_exported::MappedComparison as code;
use num_bigint::BigInt;

fn check_pair(x: BigInt, y: BigInt) {
    let expected = (x == y, (x < y, (x <= y, (x.clone().min(y.clone()), x.clone().max(y.clone())))));
    assert_eq!(code::comparison_result(x, y), expected);
}

#[test]
fn native_dictionary_comparisons_cover_nonnegative_values() {
    for x in 0..10 {
        for y in 0..10 {
            check_pair(BigInt::from(x), BigInt::from(y));
        }
    }
}

#[test]
fn native_dictionary_comparisons_keep_arbitrary_precision() {
    let huge = BigInt::from(1u8) << 200usize;
    for x in [BigInt::from(0u8), huge.clone(), huge.clone() + 1u8] {
        for y in [huge.clone() - 1u8, huge.clone(), huge.clone() + 2u8] {
            check_pair(x.clone(), y);
        }
    }
}
