// Copy into export1/tests/conditional_operand.rs after generating the matching theory.
use isabelle_exported::Conditional_Operand_Test::*;
use num_bigint::BigInt;

#[test]
fn conditionals_preserve_branch_results_in_each_position() {
    for b in [false, true] {
        for c in [false, true] {
            let tail = if b { if c { 11 } else { 13 } } else { 17 };
            assert_eq!(conditional_tail(b, c), BigInt::from(tail));
            assert_eq!(conditional_compare(b, c), tail < 13);
            assert_eq!(conditional_sum(b, c), BigInt::from(
                (if b { 2 } else { 3 }) + (if c { 5 } else { 7 })));
            let selected = if b { c } else { !c };
            assert_eq!(conditional_condition(b, c), BigInt::from(if selected { 11 } else { 17 }));
            assert_eq!(conditional_opaque(b, c), selected);
            assert_eq!(conditional_argument(b, c), BigInt::from(
                (if selected { 2 } else { 3 }) + (if c { 5 } else { 7 })));
            for d in [false, true] {
                assert_eq!(conditional_and(b, c, d), selected && d);
                assert_eq!(conditional_or(b, c, d), d || selected);
            }
        }
    }
}

#[test]
fn conditional_multiplicand_preserves_sign() {
    for value in -5..=5 {
        let x = BigInt::from(value);
        assert_eq!(conditional_product(true, x.clone()), &x * &x);
        assert_eq!(conditional_product(false, x.clone()), -(&x * &x));
    }
}
