use isabelle_exported::ProducedContainerArgument::{
    collected_values, direct_values, intersected_values, ordinary_values, tuple_values, List, Set,
};

fn values(mut list: List<bool>) -> Vec<bool> {
    let mut result = Vec::new();
    while let List::Cons(value, tail) = list {
        result.push(value);
        list = *tail;
    }
    result
}

fn contains(set: Set<bool>, value: bool) -> bool {
    match set {
        Set::Set(list) => values(list).contains(&value),
        Set::Coset(list) => !values(list).contains(&value),
    }
}

#[test]
fn direct_enum_result_keeps_all_sixteen_functions() {
    let result = values(direct_values());
    assert_eq!(result.len(), 16);
    assert_eq!(result.iter().filter(|&&value| value).count(), 8);
}

#[test]
fn ordinary_dictionary_producer_filters_without_changing_functions() {
    for input in [false, true] {
        let result = values(ordinary_values(input));
        assert_eq!(result.len(), 8);
        assert_eq!(result.iter().filter(|&&value| value).count(), 4);
    }
}

#[test]
fn collect_result_can_feed_an_existing_image() {
    for input in [false, true] {
        assert!(contains(collected_values(input), false));
        assert!(contains(collected_values(input), true));
    }
}

#[test]
fn intersection_result_can_feed_an_existing_image() {
    for input in [false, true] {
        assert!(contains(intersected_values(input), false));
        assert!(contains(intersected_values(input), true));
    }
}

#[test]
fn vimage_of_function_pairs_feeds_the_existing_image() {
    for input in [false, true] {
        assert!(contains(tuple_values(input), false));
        assert!(contains(tuple_values(input), true));
    }
}
