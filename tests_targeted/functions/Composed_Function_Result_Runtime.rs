// Runtime companion: copy to export1/tests/composed_function_result.rs.
// The HOL theorems specify map (map f). Check list contents, order, empty nested
// lists, and repeatable closure invocation at each surrounding type boundary.
use isabelle_exported::ComposedFunctionResult as code;
use std::rc::Rc;

fn list<T: Clone>(xs: &[T]) -> code::List<T> {
    xs.iter().rev().fold(code::List::Nil, |tail, x| {
        code::List::Cons(x.clone(), Box::new(tail))
    })
}

fn nested(xs: &[Vec<bool>]) -> code::List<code::List<bool>> {
    list(&xs.iter().map(|ys| list(ys)).collect::<Vec<_>>())
}

fn values<T>(mut xs: code::List<T>) -> Vec<T> {
    let mut result = Vec::new();
    while let code::List::Cons(x, tail) = xs {
        result.push(x);
        xs = *tail;
    }
    result
}

fn result(xs: code::List<code::List<bool>>) -> Vec<Vec<bool>> {
    values(xs).into_iter().map(values).collect()
}

#[test]
fn composition_preserves_the_function_result_at_all_three_boundaries() {
    let f: Rc<dyn Fn(bool) -> bool> = Rc::new(|b| !b);
    let cases = [
        vec![],
        vec![vec![]],
        vec![vec![true, false], vec![], vec![false, true, true]],
    ];
    for xs in cases {
        let expected: Vec<Vec<bool>> =
            xs.iter().map(|ys| ys.iter().map(|b| !b).collect()).collect();
        assert_eq!(result(code::composed_map(f.clone(), nested(&xs))), expected);
        assert_eq!(result(code::composed_forward(f.clone(), nested(&xs))), expected);
        match code::composed_wrapped(f.clone(), nested(&xs)) {
            code::Option::Some(ys) => assert_eq!(result(ys), expected),
            _ => panic!("the constructor boundary lost Some"),
        }
    }
}
