// Append only for exports whose source includes signed integer operations.
#[test]
fn signed_native_dictionary_operations_preserve_signs() {
    for x in -5..=5 {
        for y in -5..=5 {
            for n in 0..5 {
                check_arithmetic(BigInt::from(x), BigInt::from(y), n);
            }
        }
    }
    let huge = BigInt::from(1u8) << 200usize;
    for n in 0..4 {
        check_arithmetic(-huge.clone(), huge.clone() + 1u8, n);
    }
}
