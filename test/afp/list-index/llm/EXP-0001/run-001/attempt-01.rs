pub fn last_index<T: Eq>(xs: &[T], x: &T) -> num_bigint::BigInt {
    use num_bigint::BigInt;
    let n = xs.len();
    let mut i = n;
    for (j, y) in xs.iter().rev().enumerate() {
        if y == x {
            i = j;
            break;
        }
    }
    if i == n {
        BigInt::from(n)
    } else {
        BigInt::from(n - (i + 1))
    }
}
