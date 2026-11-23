// Copy to export1/tests/shared_default_shape.rs after generating the theory.
// The missing-equation control is not executed. Ordinary adjacent arrows must
// retain a flat two-argument Fn group; wildcard witness arguments still return
// the source Boolean result for unrelated Rust type parameters.
use isabelle_exported::SharedDefaultShape::*;
use std::rc::Rc;

#[test]
fn erased_witness_arguments_preserve_the_result() {
    assert!(witness_true::<bool>(()));
    assert!(witness_true::<Vec<bool>>(()));
    assert!(witness_true::<(bool, bool)>(()));
}

#[test]
fn adjacent_function_arrows_stay_in_one_argument_group() {
    for operation in 0..4 {
        let function: Rc<dyn Fn(bool, bool) -> bool> = Rc::new(move |x, y| {
            match operation {
                0 => x && y,
                1 => x || y,
                2 => x ^ y,
                _ => !x || y,
            }
        });
        for x in [false, true] {
            for y in [false, true] {
                let expected = match operation {
                    0 => x && y,
                    1 => x || y,
                    2 => x ^ y,
                    _ => !x || y,
                };
                assert_eq!(shape_apply(function.clone(), x, y), expected);
            }
        }
    }
}
