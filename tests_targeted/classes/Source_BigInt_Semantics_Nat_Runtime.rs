#[test]
fn natural_subtraction_truncates_at_zero() {
    for reverse_order in [false, true] {
        check_observations(code::natural_cases(reverse_order));
    }
}
