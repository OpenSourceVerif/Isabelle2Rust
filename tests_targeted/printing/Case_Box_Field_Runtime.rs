use isabelle_exported::CaseBoxField::{
    self as generated, BoxCaseTree, BranchMerge, CasePair, List, Option as HolOption, Sum, Unit,
};

// Observe the HOL tree independently of the generated Box layout. All comparisons
// below check the source values, including both alternatives of the recursive sum.
#[derive(Clone, Debug, PartialEq, Eq)]
enum View {
    Leaf(bool),
    Empty,
    Pair(Box<View>, Box<View>),
}

fn observe(tree: BoxCaseTree) -> View {
    match tree {
        BoxCaseTree::CaseLeaf(value) => View::Leaf(value),
        BoxCaseTree::CaseBranch(field) => match *field {
            Sum::Inl(Unit::Unity) => View::Empty,
            Sum::Inr((left, right)) => View::Pair(
                Box::new(observe(left)), Box::new(observe(right))),
        },
    }
}

fn construct(view: &View) -> BoxCaseTree {
    match view {
        View::Leaf(value) => BoxCaseTree::CaseLeaf(*value),
        View::Empty => BoxCaseTree::CaseBranch(Box::new(Sum::Inl(Unit::Unity))),
        View::Pair(left, right) => BoxCaseTree::CaseBranch(Box::new(
            Sum::Inr((construct(left), construct(right))))),
    }
}

fn pair(a: bool, b: bool) -> View {
    View::Pair(Box::new(View::Leaf(a)), Box::new(View::Leaf(b)))
}

fn option(value: Option<bool>) -> HolOption<bool> {
    match value {
        None => HolOption::None,
        Some(value) => HolOption::Some(value),
    }
}

fn list(values: &[bool]) -> List<bool> {
    values.iter().rev().fold(List::Nil, |tail, value|
        List::Cons(*value, Box::new(tail)))
}

#[test]
fn case_fields_preserve_values() {
    // Ordinary and nested cases cover every bool option. The constructor-only
    // case covers all payload pairs, while list lengths 0..5 exercise staged
    // matching, both successful and unsuccessful exact-length patterns.
    let options = [None, Some(false), Some(true)];
    let mut assertions = 0;
    for x in options {
        let expected = match x {
            None => View::Empty,
            Some(a) => pair(a, !a),
        };
        assert_eq!(observe(generated::ordinary_case_field(option(x))), expected);
        assertions += 1;
        for y in options {
            let expected = match x {
                None => View::Empty,
                Some(a) => pair(a, y.unwrap_or(a)),
            };
            assert_eq!(observe(generated::nested_case_field(option(x), option(y))), expected);
            assertions += 1;
        }
    }
    for a in [false, true] {
        for b in [false, true] {
            assert_eq!(observe(generated::irrefutable_case_field(CasePair::CasePair(a, b))), pair(a, b));
            assertions += 1;
        }
    }
    for len in 0..=5 {
        for bits in 0..(1usize << len) {
            let values: Vec<bool> = (0..len).map(|i| bits & (1 << i) != 0).collect();
            let expected = if len == 2 { pair(values[0], values[1]) } else { View::Empty };
            assert_eq!(observe(generated::staged_case_field(list(&values))), expected);
            assertions += 1;
        }
    }
    println!("case field value assertions: {assertions}");
}

#[test]
fn boxed_case_instance_preserves_nested_trees() {
    // Generate every tree up to two pair levels over two leaves and the empty
    // branch. Exercise direct trait dispatch and both polymorphic/concrete
    // wrappers against the source operation's three selection rules.
    let base = vec![View::Leaf(false), View::Leaf(true), View::Empty];
    let mut level_one = base.clone();
    for a in &base {
        for b in &base {
            level_one.push(View::Pair(Box::new(a.clone()), Box::new(b.clone())));
        }
    }
    let mut trees = base;
    for a in &level_one {
        for b in &level_one {
            trees.push(View::Pair(Box::new(a.clone()), Box::new(b.clone())));
        }
    }
    let mut assertions = 0;
    for left in &trees {
        for right in &trees {
            let expected = match (left, right) {
                (View::Leaf(_), _) => left.clone(),
                (_, View::Leaf(_)) => right.clone(),
                (View::Empty, _) => right.clone(),
                _ => left.clone(),
            };
            assert_eq!(observe(<BoxCaseTree as BranchMerge>::merge_branch(
                construct(left), construct(right))), expected);
            assert_eq!(observe(generated::merge_branch_values(
                construct(left), construct(right))), expected);
            assert_eq!(observe(generated::merge_case_fields(
                construct(left), construct(right))), expected);
            assertions += 3;
        }
    }
    println!("instance value assertions: {assertions}; tree inputs: {}", trees.len());
}
