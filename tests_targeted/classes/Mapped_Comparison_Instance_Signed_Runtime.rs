// Append to the shared runtime test only for integer-capable exports.
#[test]
fn signed_comparisons_use_integer_order() {
    for x in -8..=8 {
        for y in -8..=8 {
            check_pair(BigInt::from(x), BigInt::from(y));
        }
    }
    let huge = BigInt::from(1u8) << 200usize;
    check_pair(-huge.clone(), huge.clone());
    check_pair(-huge.clone(), -huge.clone() + 1u8);
    check_pair(-huge.clone(), -huge);
}
