// Copy into export1/tests/mfotl_string.rs after generating the matching theory.
// Compare the generated HOL eight-bit equality and lexicographic operations
// with Rust byte-slice operations, including high bits and embedded zeroes.
use isabelle_exported::MFOTLString::*;

fn character(n: u8) -> Char {
    Char::Char(
        n & 1 != 0, n & 2 != 0, n & 4 != 0, n & 8 != 0,
        n & 16 != 0, n & 32 != 0, n & 64 != 0, n & 128 != 0,
    )
}

fn chars(bytes: &[u8]) -> List<Char> {
    bytes.iter().rev().fold(List::Nil, |tail, &n| {
        List::Cons(character(n), Box::new(tail))
    })
}

fn compare(xs: &[u8], ys: &[u8]) {
    assert_eq!(mfotl_string8_eq(chars(xs), chars(ys)), xs == ys, "{xs:?} == {ys:?}");
    assert_eq!(mfotl_string8_le(chars(xs), chars(ys)), xs <= ys, "{xs:?} <= {ys:?}");
    assert_eq!(mfotl_string8_lt(chars(xs), chars(ys)), xs < ys, "{xs:?} < {ys:?}");
}

#[test]
fn all_eight_bit_single_character_pairs() {
    for x in 0..=255u16 {
        for y in 0..=255u16 {
            compare(&[x as u8], &[y as u8]);
        }
    }
}

#[test]
fn prefixes_embedded_zeroes_and_high_bytes() {
    // All lists of length 0..3 over this alphabet cover proper prefixes,
    // equality, and differing characters after one or two equal positions.
    let alphabet = [0, 1, 127, 128, 255];
    let mut words = Vec::new();
    for len in 0..=3u32 {
        for mut code in 0..alphabet.len().pow(len) {
            let mut word = Vec::new();
            for _ in 0..len {
                word.push(alphabet[code % alphabet.len()]);
                code /= alphabet.len();
            }
            words.push(word);
        }
    }
    for xs in &words {
        for ys in &words {
            compare(xs, ys);
        }
    }
    // Long equal prefixes exercise the recursive list path beyond the small
    // exhaustive domain, including a zero suffix and the complete byte range.
    let all: Vec<u8> = (0..=255).collect();
    let mut extended = all.clone();
    extended.push(0);
    compare(&all, &all);
    compare(&all, &extended);
    compare(&extended, &all);
}
