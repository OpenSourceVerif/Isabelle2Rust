use isabelle_exported::GuardedNullaryValue as code;

fn word(bits: usize, len: usize) -> code::List<bool> {
    (0..len).rev().fold(code::List::Nil, |xs, i| {
        code::List::Cons(bits & (1 << i) != 0, Box::new(xs))
    })
}

#[test]
fn finite_words_observe_the_hol_language_equations() {
    for len in 0..=8 {
        for bits in 0..(1 << len) {
            let xs = word(bits, len);
            assert!(!code::observe_language(xs.clone(), code::rejecting_language()));
            assert!(code::observe_language(xs.clone(), code::accepting_language()));
            assert_eq!(code::observe_language(xs.clone(), code::even_language()), len % 2 == 0);
            assert_eq!(code::observe_language(xs, code::odd_language()), len % 2 != 0);
        }
    }
}

#[test]
fn guarded_factories_construct_only_the_observed_prefix() {
    let mut empty = code::rejecting_language::<bool>();
    let mut full = code::accepting_language::<bool>();
    for i in 0..4096 {
        assert!(!code::accepting(empty.clone()));
        assert!(code::accepting(full.clone()));
        empty = code::advance(empty)(i % 2 == 0);
        full = code::advance(full)(i % 2 != 0);
    }
}

#[test]
fn cloned_transition_can_be_called_repeatedly() {
    let step = code::advance(code::accepting_language::<bool>());
    let again = step.clone();
    for x in [false, true, false, true] {
        assert!(code::accepting(step(x)));
        assert!(code::accepting(again(!x)));
    }
}
