#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Pair<A> {
    Pair(A, A),
}

fn duplicate_clone<A: Clone>(x: A) -> (A, A) {
    (x.clone(), x.clone())
}

fn duplicate_copy_specialized<A: Copy>(x: A) -> (A, A) {
    (x, x)
}

fn swap_pair<A: Copy>(p: Pair<A>) -> Pair<A> {
    match p {
        Pair::Pair(x, y) => Pair::Pair(y, x),
    }
}

fn keep_first<A>(x: A, _flag: bool) -> A {
    x
}

#[test]
fn specialized_copy_item_removes_clone_calls() {
    assert_eq!(duplicate_clone(7u32), (7, 7));
    assert_eq!(duplicate_copy_specialized(7u32), (7, 7));

    let p = Pair::Pair(true, false);
    assert_eq!(swap_pair(p), Pair::Pair(false, true));
}

#[test]
fn clone_bound_is_still_needed_for_public_generic_duplication() {
    let s = String::from("abc");
    assert_eq!(duplicate_clone(s), ("abc".to_string(), "abc".to_string()));

    let p = Pair::Pair(String::from("left"), String::from("right"));
    let _ = p.clone();
}

#[test]
fn unused_clone_bound_should_be_pruned_instead_of_changed_to_copy() {
    let s = String::from("kept");
    assert_eq!(keep_first(s, true), "kept".to_string());
}
