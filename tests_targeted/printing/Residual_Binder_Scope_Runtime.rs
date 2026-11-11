use isabelle_exported::ResidualBinderScope as code;
use code::ScopedTree as Tree;

fn bools(xs: &[bool]) -> code::List<bool> {
    xs.iter().rev().fold(code::List::Nil, |tail, &b| {
        code::List::Cons(b, Box::new(tail))
    })
}

fn list_view(xs: &code::List<bool>) -> String {
    match xs {
        code::List::Nil => String::new(),
        code::List::Cons(b, tail) => format!("{b},{}", list_view(tail)),
    }
}

fn render(t: &Tree) -> String {
    match t {
        Tree::ScopedFlag(b) => format!("F{b}"),
        Tree::ScopedPair(a, b) => format!("P{a},{b}"),
        Tree::ScopedMaybe(code::Option::None) => "N".into(),
        Tree::ScopedMaybe(code::Option::Some(b)) => format!("S{b}"),
        Tree::ScopedBind(bs, t) => format!("B[{}]({})", list_view(bs), render(t)),
        Tree::ScopedApp(l, r) => format!("A({},{})", render(l), render(r)),
    }
}

fn values() -> Vec<Tree> {
    let mut leaves = vec![Tree::ScopedMaybe(code::Option::None)];
    for a in [false, true] {
        leaves.push(Tree::ScopedFlag(a));
        leaves.push(Tree::ScopedMaybe(code::Option::Some(a)));
        for b in [false, true] {
            leaves.push(Tree::ScopedPair(a, b));
        }
    }
    let mut all = leaves.clone();
    for (i, leaf) in leaves.iter().enumerate() {
        all.push(Tree::ScopedBind(bools(&[i % 2 == 0, i % 3 == 0]), Box::new(leaf.clone())));
        all.push(Tree::ScopedApp(Box::new(leaf.clone()), Box::new(Tree::ScopedFlag(i % 2 != 0))));
    }
    all
}

#[test]
fn sibling_variants_keep_their_own_fields_in_function_and_case_fallbacks() {
    let values = values();
    for left in &values {
        for right in &values {
            let input = Tree::ScopedApp(Box::new(left.clone()), Box::new(right.clone()));
            let expected = match (left, right) {
                (Tree::ScopedFlag(true), Tree::ScopedBind(_, body)) => render(body),
                _ => render(&input),
            };
            assert_eq!(render(&code::strip_scoped_once(input.clone())), expected);
            assert_eq!(render(&code::case_scoped(input)), expected);
        }
    }
}

#[test]
fn recursive_matching_peels_only_true_flag_bind_pairs() {
    for leaf in values() {
        let mut nested = leaf.clone();
        for _ in 0..8 {
            nested = Tree::ScopedApp(
                Box::new(Tree::ScopedFlag(true)),
                Box::new(Tree::ScopedBind(bools(&[true, false]), Box::new(nested))),
            );
        }
        assert_eq!(render(&code::strip_scoped(nested.clone())), render(&leaf));
        let blocked = Tree::ScopedApp(
            Box::new(Tree::ScopedFlag(false)),
            Box::new(Tree::ScopedBind(bools(&[false, true]), Box::new(nested))),
        );
        assert_eq!(render(&code::strip_scoped(blocked.clone())), render(&blocked));
    }
}

#[test]
fn non_application_roots_preserve_their_payloads() {
    for value in values() {
        if !matches!(&value, Tree::ScopedApp(_, _)) {
            let expected = render(&value);
            assert_eq!(render(&code::strip_scoped(value.clone())), expected);
            assert_eq!(render(&code::strip_scoped_once(value.clone())), expected);
            assert_eq!(render(&code::case_scoped(value)), expected);
        }
    }
}
