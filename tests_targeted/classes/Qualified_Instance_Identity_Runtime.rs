// Copy into export1/tests/qualified_instance_identity.rs after generating.
// Both methods must survive for both same-base-name types. Vec<bool> has no
// Probe implementation: using it as Right's payload also checks that Left's
// payload constraint is not merged into Right's impl or exported wrappers.
use isabelle_exported::QualifiedInstanceIdentity::{
    flip_left, flip_right, left_values, read_left, read_right, right_values,
    Probe, Token, Tokena,
};

#[test]
fn left_methods_delegate_through_nested_instances() {
    for value in [false, true] {
        let token = Token::LeftToken(value);
        assert_eq!(left_values(value), (value, !value));
        assert_eq!(read_left(token.clone()), value);
        assert_eq!(flip_left(token.clone()), !value);
        assert_eq!(<Token<bool> as Probe>::read_probe(token.clone()), value);
        assert_eq!(<Token<bool> as Probe>::flip_probe(token.clone()), !value);
        assert_eq!(read_left(Token::LeftToken(token.clone())), value);
        assert_eq!(flip_left(Token::LeftToken(token)), !value);
    }
}

#[test]
fn right_methods_do_not_require_payload_instances() {
    // 31 distinct vectors, both Boolean fields, seven observations: 434 checks.
    for len in 0..=4 {
        for mask in 0..(1usize << len) {
            let payload: Vec<bool> = (0..len).map(|bit| mask & (1 << bit) != 0).collect();
            for value in [false, true] {
                let token = Tokena::RightToken(value, payload.clone());
                assert_eq!(right_values(value, payload.clone()), (value, !value));
                assert_eq!(read_right(token.clone()), value);
                assert_eq!(flip_right(token.clone()), !value);
                assert_eq!(<Tokena<Vec<bool>> as Probe>::read_probe(token.clone()), value);
                assert_eq!(<Tokena<Vec<bool>> as Probe>::flip_probe(token.clone()), !value);
                assert_eq!(read_left(Token::LeftToken(token.clone())), value);
                assert_eq!(flip_left(Token::LeftToken(token)), !value);
            }
        }
    }
}
