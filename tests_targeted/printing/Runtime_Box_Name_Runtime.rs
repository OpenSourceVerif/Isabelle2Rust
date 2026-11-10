// Copy into export1/tests/runtime_box_name.rs after generating the theory.
// Keep the HOL Box visible under its own name and use an explicit alias for
// the heap allocator. Independent Vec expectations check recursive construction,
// nested pattern extraction and rebuilding, plus a generic user-Box payload.
use isabelle_exported::RuntimeBoxName::{self as generated, Box, Spine};
use std::boxed::Box as Heap;

fn spine(bits: &[bool]) -> Spine {
    bits.iter().rev().fold(Spine::Stop, |tail, bit| {
        Spine::Step(*bit, Heap::new(tail))
    })
}

fn bits(mut value: Spine) -> Vec<bool> {
    let mut result = Vec::new();
    while let Spine::Step(bit, tail) = value {
        result.push(bit);
        value = *tail;
    }
    result
}

#[test]
fn recursive_fields_and_user_box_remain_distinct() {
    // All 511 Boolean vectors of lengths zero through eight; five checks each.
    for len in 0..=8 {
        for mask in 0..(1usize << len) {
            let input: Vec<bool> = (0..len).map(|bit| mask & (1 << bit) != 0).collect();
            let inverted: Vec<bool> = input.iter().map(|bit| !bit).collect();
            let pair = if len >= 2 { (input[0], input[1]) } else { (false, false) };
            assert_eq!(bits(generated::unpack(Box::UserBox(spine(&input)))), input);
            assert_eq!(bits(generated::flip(spine(&input))), inverted);
            assert_eq!(bits(generated::flip(generated::flip(spine(&input)))), input);
            assert_eq!(generated::inspect(Box::UserBox(spine(&input))), pair);
            assert_eq!(generated::unpack(Box::UserBox(input.clone())), input);
        }
    }
}

#[test]
fn generated_nested_construction_matches_inputs() {
    for first in [false, true] {
        for second in [false, true] {
            assert_eq!(generated::inspect(generated::pack(first, second)), (first, second));
            assert_eq!(bits(generated::unpack(generated::pack(first, second))), vec![first, second]);
        }
    }
}
