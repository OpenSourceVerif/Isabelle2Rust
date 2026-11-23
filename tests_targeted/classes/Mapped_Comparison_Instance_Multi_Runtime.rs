use isabelle_exported::Mapped_Comparison_Instance_Test as code;
use num_bigint::BigInt;

#[test]
fn mapped_comparison_impls_are_available_across_modules() {
    let x = BigInt::from(-3);
    let y = BigInt::from(2);
    let expected = (false, (true, (true, (x.clone(), y.clone()))));
    assert_eq!((*code::integer_comparison(x.clone()))(y.clone()), expected);
    assert_eq!((*code::int_comparison(x))(y), expected);
    let one = BigInt::from(1);
    assert_eq!((*code::nat_comparison(one.clone()))(one.clone()),
        (true, (false, (true, (one.clone(), one)))));
}
