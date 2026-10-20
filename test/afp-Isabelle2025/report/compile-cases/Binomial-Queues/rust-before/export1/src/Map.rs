use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::Option::Option;

pub fn map_of <B, A> (x0: List<(A, B)>, k: A) -> Option<B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (x0, k) {
        (List::Cons ((l, v), p0), k) =>
            {
                let ps = *p0;
                if eq(l.clone(), k.clone()) {
                    Option::Some (v.clone())
                } else {
                    map_of(ps.clone(), k.clone())
                }
            },
        (List::Nil, _) =>
            Option::None,
        _ =>
            panic!("non-exhaustive match")
    }
}
