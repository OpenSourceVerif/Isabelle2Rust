#[test]
fn conversions_arithmetic_division_and_bits_match_hol() {
    for b in [false, true] {
        let mut xs = code::arithmetic_observations(b);
        let mut count = 0;
        while let code::List::Cons(value, rest) = xs {
            assert!(value, "arithmetic observation {count}, negative={b}");
            xs = *rest;
            count += 1;
        }
        assert_eq!(count, 21);
    }
    let mut xs = code::mixed_container_observations();
    let mut count = 0;
    while let code::List::Cons(value, rest) = xs {
        assert!(value);
        xs = *rest;
        count += 1;
    }
    assert_eq!(count, 4);
}
#[test]
fn source_wrappers_are_distinct_and_nat_boundary_enforces_nonnegativity() {
    use isabelle_exported::Rust_Source_BigInt::{Nat, Int, Integer};
    use num_bigint::BigInt;
    use std::any::TypeId;
    assert_ne!(TypeId::of::<Nat>(), TypeId::of::<Int>());
    assert_ne!(TypeId::of::<Int>(), TypeId::of::<Integer>());
    assert_ne!(TypeId::of::<Nat>(), TypeId::of::<Integer>());
    assert_eq!(Nat::from_bigint(BigInt::from(-1)).into_bigint(), BigInt::from(0));
    assert_eq!((Nat::from_bigint(BigInt::from(1)) - Nat::from_bigint(BigInt::from(2))).into_bigint(), BigInt::from(0));
    assert_eq!((Int::from_bigint(BigInt::from(1)) - Int::from_bigint(BigInt::from(2))).into_bigint(), BigInt::from(-1));
}
