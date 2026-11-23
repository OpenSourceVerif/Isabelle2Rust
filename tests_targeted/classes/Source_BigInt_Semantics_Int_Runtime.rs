#[test]
fn int_subtraction_preserves_negative_results() {
    for reverse_order in [false, true] {
        check_observations(code::int_cases(reverse_order));
    }
}
