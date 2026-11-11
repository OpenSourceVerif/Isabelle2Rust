use isabelle_exported::ContextualNullaryMethodStandalone as code;

fn contains(set: code::Set<bool>, value: bool) -> bool {
    let (mut xs, inverted) = match set {
        code::Set::Set(xs) => (xs, false),
        code::Set::Coset(xs) => (xs, true),
    };
    let mut found = false;
    while let code::List::Cons(x, tail) = xs {
        found |= x == value;
        xs = *tail;
    }
    found != inverted
}

#[test]
fn observations_do_not_depend_on_exporting_the_generic_bottom() {
    for a in [false, true] {
        for b in [false, true] {
            for value in [false, true] {
                assert_eq!(
                    contains(code::relation_observations(a, b), value),
                    value == (a && b) || value == (a || b),
                );
            }
        }
    }
}
