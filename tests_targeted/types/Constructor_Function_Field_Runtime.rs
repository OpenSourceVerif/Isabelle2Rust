// Exhaust the finite Boolean observations proved in the HOL theory.
// Reuse every callback and returned function: captures must remain cloneable.
use isabelle_exported::ConstructorFunctionField as code;
use std::rc::Rc;

fn boolean_function(table: u8) -> Rc<dyn Fn(bool) -> bool> {
    Rc::new(move |x: bool| table & (1 << u8::from(x)) != 0)
}

#[test]
fn lens_getters_and_function_valued_setters_keep_their_boundaries() {
    for k in [false, true] {
        let code::FieldLens::FieldLens(get, put) = code::bool_function_field_lens(k);
        for table in 0..4 {
            let f = boolean_function(table);
            assert_eq!(get(f.clone()), f(k));
            for v in [false, true] {
                let updated = put(f.clone(), v);
                for x in [false, true] {
                    let expected = if x == k { v } else { f(x) };
                    assert_eq!(updated(x), expected);
                    assert_eq!(updated(x), expected);
                    assert_eq!(code::apply_field_lens(k, f.clone(), v, x), (f(k), expected));
                }
            }
        }
    }
}

#[test]
fn getter_field_returns_a_reusable_function() {
    let boxed = code::returning_function_field();
    let code::OutputField::OutputField(get) = boxed.clone();
    for x in [false, true] {
        let f = get(x);
        for y in [false, true] {
            assert_eq!(f(y), x != y);
            assert_eq!(f(y), x != y);
            assert_eq!(code::apply_output_field(boxed.clone(), x, y), x != y);
        }
    }
}

#[test]
fn binary_function_operation_returns_the_function_result() {
    let boxed = code::function_operation_field();
    let code::OperationField::OperationField(combine) = boxed.clone();
    for left in 0..4 {
        for right in 0..4 {
            let f = boolean_function(left);
            let g = boolean_function(right);
            let combined = combine(f.clone(), g.clone());
            for x in [false, true] {
                let expected = if x { g(x) } else { f(x) };
                assert_eq!(combined(x), expected);
                assert_eq!(combined(x), expected);
                assert_eq!(code::apply_operation_field(boxed.clone(), f.clone(), g.clone(), x), expected);
            }
        }
    }
}
