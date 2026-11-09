// Copy this file to export1/tests/ads_list.rs after generating
// ADS_List_Equations_Test. These tests compare the generated representation
// with ordinary Rust vectors, including every Boolean list of length <= 6.
// The merge oracle is semantic equality of the input vectors, independent of
// the generated recursive sum/product implementation.
use isabelle_exported::ADSList::*;

fn values<A>(list: List<A>) -> Vec<A> {
    let List::ListR1ToList(mut node) = list;
    let mut result = Vec::new();
    loop {
        let ListR1::ListR1(layer) = node;
        match *layer {
            Sum::Inl(Unit::Unity) => return result,
            Sum::Inr((head, tail)) => {
                result.push(head);
                node = tail;
            }
        }
    }
}

fn input(xs: &[bool]) -> List<bool> {
    xs.iter().rev().fold(ads_empty(), |tail, x| ads_prepend(*x, tail))
}

fn samples() -> Vec<Vec<bool>> {
    (0..=6)
        .flat_map(|len| {
            (0..(1 << len))
                .map(move |bits| (0..len).map(|i| bits & (1 << i) != 0).collect())
        })
        .collect()
}

#[test]
fn construction_and_inverse_preserve_elements() {
    for xs in samples() {
        assert_eq!(values(input(&xs)), xs);
        assert_eq!(values(ads_wrap(ads_rep(input(&xs)))), xs);
        for x in [false, true] {
            let mut expected = vec![x];
            expected.extend(&xs);
            assert_eq!(values(ads_prepend(x, input(&xs))), expected);
        }
    }
    for x in [false, true] {
        for y in [false, true] {
            for z in [false, true] {
                assert_eq!(values(ads_triple(x, y, z)), vec![x, y, z]);
            }
        }
    }
}

#[test]
fn lifted_merge_preserves_success_and_failure() {
    let all = samples();
    for xs in &all {
        for ys in &all {
            let actual = match (*ads_merge(input(xs)))(input(ys)) {
                Option::None => std::option::Option::None,
                Option::Some(result) => std::option::Option::Some(values(result)),
            };
            let expected = if xs == ys { Some(xs.clone()) } else { None };
            assert_eq!(actual, expected, "merge({xs:?}, {ys:?})");
        }
    }
}

// Decode the generated HOL literal and typerep to check the complete nested
// value. A successful export alone would not detect lost type arguments,
// reordered children, or an accidentally empty list of arguments.
fn literal(mut text: Literal) -> String {
    let mut bytes = Vec::new();
    loop {
        match text {
            Literal::ZeroLiteral => return String::from_utf8(bytes).unwrap(),
            Literal::Literal(a, b, c, d, e, f, g, tail) => {
                let bits = [a, b, c, d, e, f, g];
                bytes.push(bits.iter().enumerate().fold(0, |v, (i, bit)| {
                    v | ((*bit as u8) << i)
                }));
                text = *tail;
            }
        }
    }
}

#[derive(Debug, PartialEq)]
struct TypeTree(String, Vec<TypeTree>);

fn type_tree(value: Typerepa) -> TypeTree {
    let Typerepa::Typerep(name, args) = value;
    TypeTree(literal(name), values(*args).into_iter().map(type_tree).collect())
}

#[test]
fn typerep_retains_hol_names_and_nested_arguments() {
    assert_eq!(
        type_tree(ads_type()),
        TypeTree(
            "Product_Type.prod".into(),
            vec![
                TypeTree("List.list".into(), vec![TypeTree("HOL.bool".into(), vec![])]),
                TypeTree("Product_Type.unit".into(), vec![]),
            ],
        )
    );
}
