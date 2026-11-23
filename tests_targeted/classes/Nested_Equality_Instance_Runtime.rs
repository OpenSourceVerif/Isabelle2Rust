// Copy into export1/tests/nested_equality_instance.rs after generating the theory.
// Compare the generated mutually recursive term/list equality against Rust's
// derived structural equality on an independent, Vec-based reference tree.
use isabelle_exported::NestedEqualityInstance::*;

#[derive(Clone, Debug, PartialEq, Eq)]
enum Model {
    Var(bool),
    Fun(bool, Vec<Model>),
}

fn generated(tree: &Model) -> EqualityTerm<bool, bool> {
    match tree {
        Model::Var(v) => EqualityTerm::EVar(*v),
        Model::Fun(label, children) => {
            let list = children.iter().rev().fold(List::Nil, |tail, child| {
                List::Cons(generated(child), Box::new(tail))
            });
            EqualityTerm::EFun(*label, Box::new(list))
        }
    }
}

#[test]
fn exhaustive_small_terms_match_structural_equality() {
    let leaves = vec![
        Model::Var(false),
        Model::Var(true),
        Model::Fun(false, vec![]),
        Model::Fun(true, vec![]),
    ];
    let mut corpus = leaves.clone();
    for label in [false, true] {
        for left in &leaves {
            corpus.push(Model::Fun(label, vec![left.clone()]));
            for right in &leaves {
                corpus.push(Model::Fun(label, vec![left.clone(), right.clone()]));
            }
        }
    }
    // 44 trees, every ordered pair, through both generic and concrete roots.
    for left in &corpus {
        for right in &corpus {
            let expected = left == right;
            assert_eq!(compare_terms(generated(left), generated(right)), expected);
            assert_eq!(compare_bool_terms(generated(left), generated(right)), expected);
        }
    }
}

#[test]
fn recursive_children_labels_and_lengths() {
    let mut tree = Model::Var(false);
    for depth in 1..=8 {
        let label = depth % 2 == 0;
        let children = vec![Model::Var(label), tree];
        tree = Model::Fun(label, children.clone());
        let wrong_label = Model::Fun(!label, children);
        let shorter = Model::Fun(label, vec![Model::Var(label)]);
        assert!(<EqualityTerm<bool, bool> as Equal>::equal(generated(&tree), generated(&tree)));
        assert!(!compare_bool_terms(generated(&tree), generated(&wrong_label)));
        assert!(!compare_bool_terms(generated(&tree), generated(&shorter)));
        assert!(!compare_bool_terms(generated(&tree), generated(&Model::Var(label))));
    }
}
