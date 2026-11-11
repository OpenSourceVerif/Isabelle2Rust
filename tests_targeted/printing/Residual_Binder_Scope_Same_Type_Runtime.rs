use isabelle_exported::SameTypeBinderScope as code;
use code::SameScopedTree as Tree;

fn render(t: &Tree) -> String {
    match t {
        Tree::SameFlag(b) => format!("F{b}"),
        Tree::SameOther(b) => format!("O{b}"),
        Tree::SameBind(b, t) => format!("B{b}({})", render(t)),
        Tree::SameApp(l, r) => format!("A({},{})", render(l), render(r)),
    }
}

#[test]
fn same_typed_sibling_fields_do_not_silently_replace_each_other() {
    for left in [false, true] {
        for right in [false, true] {
            let value = Tree::SameApp(
                Box::new(Tree::SameOther(left)),
                Box::new(Tree::SameFlag(right)),
            );
            assert_eq!(render(&code::strip_same_scoped(value.clone())), render(&value));
        }
    }
}

#[test]
fn every_nonmatching_constructor_combination_preserves_its_payload() {
    let mut values = vec![];
    for b in [false, true] {
        values.push(Tree::SameFlag(b));
        values.push(Tree::SameOther(b));
        values.push(Tree::SameBind(b, Box::new(Tree::SameOther(!b))));
        values.push(Tree::SameApp(Box::new(Tree::SameOther(b)), Box::new(Tree::SameFlag(!b))));
    }
    for left in &values {
        for right in &values {
            let value = Tree::SameApp(Box::new(left.clone()), Box::new(right.clone()));
            let expected = match (left, right) {
                (Tree::SameFlag(true), Tree::SameBind(_, body)) => render(body),
                _ => render(&value),
            };
            assert_eq!(render(&code::strip_same_scoped(value)), expected);
        }
    }
}
