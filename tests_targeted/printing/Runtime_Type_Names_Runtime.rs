// Runtime companion for export6: each observation agrees with observable_results.
// The generic clone control also uses a Clone but non-Copy Rust value.
use isabelle_exported::RuntimeTypeNames as code;
use num_bigint::BigInt;

#[test]
fn source_rc_values_survive_closure_capture() {
    for b in [false, true] {
        assert_eq!(code::rc_roundtrip(b), b);
    }
}

#[test]
fn source_big_int_and_runtime_integer_remain_distinct() {
    for b in [false, true] {
        for n in [-257, 0, 513] {
            assert_eq!(code::numeric_roundtrip(b, BigInt::from(n)),
                       (b, BigInt::from(n + 1)));
        }
    }
}

#[test]
fn source_clone_type_does_not_replace_the_clone_bound() {
    for b in [false, true] {
        assert_eq!(code::clone_roundtrip(b), b);
    }
    let payload = String::from("non-Copy payload");
    assert_eq!(code::clone_roundtrip(payload.clone()), payload);
}

#[test]
fn source_fn_values_do_not_replace_the_function_trait() {
    for b in [false, true] {
        assert_eq!(code::fn_roundtrip(b), b);
    }
}

#[test]
fn source_phantom_data_and_runtime_marker_remain_distinct() {
    for b in [false, true] {
        assert_eq!(code::phantom_observe(code::phantom_collision(b)), b);
    }
}
