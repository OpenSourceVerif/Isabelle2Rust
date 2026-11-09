// Copy into export1/tests/case_operand.rs after generating the matching theory.
// Independently compute each branch result and check operator grouping for
// ordinary matches, irrefutable blocks, and nested boxed-pattern matches.
use isabelle_exported::CaseOperand::*;
use num_bigint::BigInt;

fn choices() -> Vec<(OperandChoice, Option<bool>)> {
    vec![(OperandChoice::Skip, None), (OperandChoice::Take(false), Some(false)),
         (OperandChoice::Take(true), Some(true))]
}

#[test]
fn boolean_cases_preserve_operand_grouping() {
    for (c, value) in choices() {
        for b in [false, true] {
            assert_eq!(case_and(c.clone(), b), value.unwrap_or(true) && b);
            assert_eq!(case_or(c.clone(), b), value.unwrap_or(false) || b);
            assert_eq!(case_right(c.clone(), b), b && value.unwrap_or(true));
            for (d, other) in choices() {
                let branch = match value {
                    Some(x) => other.unwrap_or(true) && x,
                    None => b,
                };
                assert_eq!(case_nested(c.clone(), d, b), branch || b);
            }
        }
    }
}

#[test]
fn arithmetic_match_and_irrefutable_block_are_operands() {
    for (c, value) in choices() {
        let base = match value { Some(true) => 2, Some(false) => 5, None => -3 };
        for k in [-17, -1, 0, 1, 23] {
            assert_eq!(case_arithmetic(c.clone(), BigInt::from(k)), BigInt::from(base + k));
        }
    }
    for x in [false, true] {
        for y in [false, true] {
            for b in [false, true] {
                assert_eq!(case_pair((x, y), b), (x || y) && b);
                assert_eq!(case_binding(OperandPair::Pair(x, y), b), (x || y) && b);
            }
        }
    }
}

fn tree_value(t: &OperandTree) -> bool {
    match t {
        OperandTree::Leaf(x) => *x,
        OperandTree::Branch(left, right) => match (left.as_ref(), right.as_ref()) {
            (OperandTree::Leaf(x), OperandTree::Leaf(y)) => *x && *y,
            _ => false,
        },
    }
}

#[test]
fn nested_boxed_patterns_preserve_following_operator() {
    let leaves = vec![OperandTree::Leaf(false), OperandTree::Leaf(true)];
    let mut shallow = leaves.clone();
    for left in &leaves {
        for right in &leaves {
            shallow.push(OperandTree::Branch(Box::new(left.clone()), Box::new(right.clone())));
        }
    }
    let mut trees = shallow.clone();
    for left in &shallow {
        for right in &shallow {
            trees.push(OperandTree::Branch(Box::new(left.clone()), Box::new(right.clone())));
        }
    }
    for t in trees {
        for b in [false, true] {
            assert_eq!(case_tree(t.clone(), b), tree_value(&t) && b);
        }
    }
}
