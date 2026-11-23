use isabelle_exported::ConditionalGuardedValue as code;

fn word(bits: usize, len: usize) -> code::List<bool> {
    (0..len).rev().fold(code::List::Nil, |xs, i| {
        code::List::Cons(bits & (1 << i) != 0, Box::new(xs))
    })
}

#[test]
fn both_conditions_follow_the_proved_hol_observations() {
    for len in 0..=8 {
        for bits in 0..(1 << len) {
            let xs = word(bits, len);
            assert!(code::observe_language(xs.clone(), code::conditional_language()));
            assert_eq!(
                code::observe_language(xs, code::conditional_stopping()),
                len == 0,
            );
        }
    }
}

#[test]
fn selecting_a_recursive_callback_constructs_only_the_observed_prefix() {
    let mut continuing = code::conditional_language::<bool>();
    let mut stopping = code::conditional_stopping::<bool>();
    for i in 0..4096 {
        assert!(code::accepting(continuing.clone()));
        assert_eq!(code::accepting(stopping.clone()), i == 0);
        continuing = code::advance(continuing)(i % 2 == 0);
        stopping = code::advance(stopping)(i % 2 != 0);
    }
}

#[test]
fn selected_callbacks_remain_reusable_after_cloning() {
    for (language, expected) in [
        (code::conditional_language::<bool>(), true),
        (code::conditional_stopping::<bool>(), false),
    ] {
        let step = code::advance(language);
        let again = step.clone();
        for x in [false, true, false, true] {
            assert_eq!(code::accepting(step(x)), expected);
            assert_eq!(code::accepting(again(!x)), expected);
        }
    }
}
