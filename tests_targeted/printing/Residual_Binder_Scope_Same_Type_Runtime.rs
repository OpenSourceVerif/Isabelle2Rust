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

fn values() -> Vec<Tree> {
    let mut values = vec![];
    for b in [false, true] {
        values.push(Tree::SameFlag(b));
        values.push(Tree::SameOther(b));
        values.push(Tree::SameBind(b, Box::new(Tree::SameOther(!b))));
        values.push(Tree::SameApp(Box::new(Tree::SameOther(b)), Box::new(Tree::SameFlag(!b))));
    }
    values
}

#[test]
fn every_nonmatching_constructor_combination_preserves_its_payload() {
    let values = values();
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

#[test]
fn repeated_names_in_several_equations_retain_their_field_positions() {
    let values = values();
    for left in &values {
        for right in &values {
            let input = Tree::SameApp(Box::new(left.clone()), Box::new(right.clone()));
            let expected = match (left, right) {
                (Tree::SameFlag(a), Tree::SameOther(b)) => format!("A(O{a},F{b})"),
                (Tree::SameOther(a), Tree::SameFlag(b)) => format!("A(F{b},O{a})"),
                (Tree::SameBind(a, body), Tree::SameFlag(b)) => {
                    format!("A(B{b}({}),O{a})", render(body))
                }
                _ => render(&input),
            };
            assert_eq!(render(&code::named_rows(input)), expected);
        }
    }
}

#[test]
fn case_alternatives_keep_enclosing_names_separate_from_field_names() {
    let values = values();
    for p1 in [false, true] {
        for whole1 in [false, true] {
            for left in &values {
                for right in &values {
                    let input = Tree::SameApp(Box::new(left.clone()), Box::new(right.clone()));
                    let expected = match (left, right) {
                        (Tree::SameFlag(a), Tree::SameOther(b)) => {
                            format!("A(B{p1}(F{a}),B{whole1}(O{b}))")
                        }
                        (Tree::SameOther(a), Tree::SameFlag(b)) => {
                            format!("A(B{p1}(O{b}),B{whole1}(F{a}))")
                        }
                        (Tree::SameBind(a, body), Tree::SameFlag(b)) => {
                            format!("A(B{p1}(B{a}({})),B{whole1}(F{b}))", render(body))
                        }
                        _ => format!("A(F{p1},A(O{whole1},{}))", render(&input)),
                    };
                    assert_eq!(render(&code::case_with_outer_names(p1, whole1, input)), expected);
                }
            }
        }
    }
}
