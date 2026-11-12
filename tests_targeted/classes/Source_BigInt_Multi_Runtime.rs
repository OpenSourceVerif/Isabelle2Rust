use isabelle_exported::Source_BigInt_Semantics_Test as code;
use isabelle_exported::List::List;
fn check(mut xs: List<bool>, expected: usize) {
    let mut count = 0;
    while let List::Cons(value, tail) = xs {
        assert!(value, "observation {count}");
        count += 1;
        xs = *tail;
    }
    assert_eq!(count, expected);
}
#[test]
fn distinct_source_instances_work_across_generated_modules() {
    for reverse in [false, true] {
        check(code::natural_cases(reverse), 6);
        check(code::int_cases(reverse), 6);
        check(code::integer_cases(reverse), 6);
        check(code::arithmetic_observations(reverse), 21);
    }
    check(code::mixed_container_observations(), 4);
}
