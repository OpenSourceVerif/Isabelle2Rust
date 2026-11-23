// Copy into export1/tests/instance_receiver_position.rs after generating.
// These factories return the user-defined prod/option inside the standard
// option and tuple wrappers. Check both exported wrappers and trait dispatch;
// unrelated Rust payload types also ensure the impl keeps its own parameters.
use isabelle_exported::InstanceReceiverPosition::{
    bool_seed, option_seed, product_seed, NestedSeed, Option as HolOption, Optiona, Prod,
};

fn check_product<A: Clone + 'static, B: Clone + 'static>() {
    let (value, flag): (HolOption<Prod<A, B>>, bool) = product_seed();
    assert!(matches!(value, HolOption::Some(Prod::EmptyProduct)));
    assert!(flag);
    let (value, flag) = <Prod<A, B> as NestedSeed>::nested_seed();
    assert!(matches!(value, HolOption::Some(Prod::EmptyProduct)));
    assert!(flag);
}

fn check_option<A: Clone + 'static>() {
    let (value, flag): (HolOption<Optiona<A>>, bool) = option_seed();
    assert!(matches!(value, HolOption::Some(Optiona::EmptyOption)));
    assert!(!flag);
    let (value, flag) = <Optiona<A> as NestedSeed>::nested_seed();
    assert!(matches!(value, HolOption::Some(Optiona::EmptyOption)));
    assert!(!flag);
}

#[test]
fn product_carrier_inside_standard_product() {
    check_product::<bool, u8>();
    check_product::<Vec<bool>, String>();
    check_product::<(bool, u8), Vec<u8>>();
}

#[test]
fn option_carrier_inside_standard_option() {
    check_option::<bool>();
    check_option::<Vec<bool>>();
    check_option::<String>();
}

#[test]
fn unambiguous_boolean_instance_is_preserved() {
    for (value, flag) in [bool_seed(), <bool as NestedSeed>::nested_seed()] {
        assert!(matches!(value, HolOption::Some(true)));
        assert!(flag);
    }
}
