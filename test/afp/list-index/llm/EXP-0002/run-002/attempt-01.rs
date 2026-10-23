pub fn last_index<T: Eq>(xs: &[T], x: &T) -> num_bigint::BigInt {
    let n = xs.len();
    let mut i = n;
    for (j, y) in xs.iter().rev().enumerate() {
        if y == x {
            i = j;
            break;
        }
    }
    if i == n {
        num_bigint::BigInt::from(n)
    } else {
        num_bigint::BigInt::from(n - (i + 1))
    }
}
