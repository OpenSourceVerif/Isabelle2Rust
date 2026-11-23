#[test]
fn integer_subtraction_preserves_negative_results() {
    for reverse_order in [false, true] {
        check_observations(code::integer_cases(reverse_order));
    }
}
