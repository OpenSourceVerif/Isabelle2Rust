use crate::Arith::AbSemigroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::MonoidAdd;
use crate::Arith::Plus;
use crate::Arith::SemigroupAdd;
use crate::Arith::Zero;
use crate::Groups_List::sum_list;
use crate::List::List;
use crate::List::append;
use crate::Set::Set;

#[derive(Clone)]
pub enum Multiset<A> {
    Mset (List<A>)
}

impl <A : Clone + 'static> Plus for Multiset<A> {
    fn plus (x0: Multiset<A>, x1: Multiset<A>) -> Multiset<A> {
        let (Multiset::Mset (xs), Multiset::Mset (ys)) = (x0, x1);
        Multiset::Mset (append(xs.clone(), ys.clone()))
    }
}

impl <A : Clone + 'static> Zero for Multiset<A> {
    fn zero () -> Multiset<A> {
        Multiset::Mset (List::Nil)
    }
}

pub fn add_mset <A> (x: A, xa1: Multiset<A>) -> Multiset<A>
where
    A : Clone + 'static
{
    let (x, Multiset::Mset (xs)) = (x, xa1);
    Multiset::Mset (List::Cons (x.clone(), Box::new(xs.clone())))
}

pub fn set_mset <A> (x0: Multiset<A>) -> Set<A>
where
    A : Clone + 'static
{
    let Multiset::Mset (xs) = x0;
    Set::Set (xs.clone())
}

pub fn sum_mset <A> (x0: Multiset<A>) -> A
where
    A : Clone + CommMonoidAdd + 'static
{
    let Multiset::Mset (xs) = x0;
    sum_list(xs.clone())
}
