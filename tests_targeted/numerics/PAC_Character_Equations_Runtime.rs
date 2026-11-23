// Copy to export1/tests/pac_character.rs after generating the matching theory.
// HOL char is an eight-bit value, whereas String.literal contains seven-bit
// characters. Check the complete char domain and independently compute the
// actual PAC literal hash with Rust's wrapping u32 arithmetic.
use isabelle_exported::PACCharacter::*;
use num_bigint::BigInt;

fn character(n: u8) -> Char {
    Char::Char(
        n & 1 != 0, n & 2 != 0, n & 4 != 0, n & 8 != 0,
        n & 16 != 0, n & 32 != 0, n & 64 != 0, n & 128 != 0,
    )
}

fn literal(bytes: &[u8]) -> Literal {
    bytes.iter().rev().fold(Literal::ZeroLiteral, |tail, &n| {
        assert!(n < 128);
        Literal::Literal(
            n & 1 != 0, n & 2 != 0, n & 4 != 0, n & 8 != 0,
            n & 16 != 0, n & 32 != 0, n & 64 != 0, Box::new(tail),
        )
    })
}

#[test]
fn every_eight_bit_character_preserves_its_unsigned_value() {
    for n in 0..=255u16 {
        let expected = BigInt::from(n);
        assert_eq!(pac_char_value(character(n as u8)), expected);
        // Observe the separately exported word result as well, so the test
        // also covers the uint32 boundary instead of only the integer wrapper.
        assert_eq!(integer_of_uint32(pac_char_word(character(n as u8))), expected);
    }
}

fn check_hash(bytes: &[u8]) {
    let expected = bytes.iter().fold(5381u32, |h, &c| {
        h.wrapping_mul(33).wrapping_add(u32::from(c))
    });
    assert_eq!(pac_hash_value(literal(bytes)), BigInt::from(expected), "{bytes:?}");
}

#[test]
fn literal_hash_matches_wrapping_u32_arithmetic() {
    for n in 0..=127 {
        check_hash(&[n]);
    }
    // All length-0..4 strings over this alphabet include embedded NUL,
    // control characters, spaces, letters and DEL, and cross the sign bit.
    let alphabet = [0, 1, 32, 65, 127];
    for len in 0..=4u32 {
        for mut code in 0..5usize.pow(len) {
            let mut bytes = Vec::new();
            for _ in 0..len {
                bytes.push(alphabet[code % alphabet.len()]);
                code /= alphabet.len();
            }
            check_hash(&bytes);
        }
    }
    check_hash(&(0..=127).collect::<Vec<_>>());
    check_hash(&vec![127; 256]);
}
