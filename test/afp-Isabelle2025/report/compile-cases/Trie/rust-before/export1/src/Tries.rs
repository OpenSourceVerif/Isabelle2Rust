use crate::Complete_Lattices::sup_set;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::fold;
use crate::List::list_all;
use crate::Option::Option;
use crate::Set::Set;
use crate::Set::image;
use crate::Set::top_set;
use crate::Trie::Trie;
use crate::Trie::all_trie;
use crate::Trie::lookup_trie;
use crate::Trie::update_with_trie;

use std::rc::Rc;

pub fn all_tries <A, B>
    (p: Rc<dyn Fn(A) -> bool>) -> Rc<dyn Fn(Trie<B, List<A>>) -> bool>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    (({
        let p_cap = p.clone();
        Rc::new(move |a: Trie<B, List<A>>| -> bool {
            all_trie((({
                let p_capa = p_cap.clone();
                Rc::new(move |aa: List<A>| -> bool {
                    list_all(p_capa.clone(), aa.clone())
                })
            }) as Rc<dyn Fn(List<A>) -> bool>), a.clone())
        })
    }) as Rc<dyn Fn(Trie<B, List<A>>) -> bool>)
}

pub fn lookup_tries <B, A> (t: Trie<A, List<B>>, ks: List<A>) -> List<B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match lookup_trie(t.clone(), ks.clone()) {
        Option::None =>
            List::Nil,
        Option::Some (vs) =>
            vs.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set_tries <B, A> (t: Trie<A, List<B>>) -> Set<B>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    sup_set(image(
        (({
            let t_cap = t.clone();
            Rc::new(move |a: List<A>| -> Set<B> {
                Set::Set (lookup_tries(t_cap.clone(), a.clone()))
            })
        }) as Rc<dyn Fn(List<A>) -> Set<B>>),
        top_set::<List<A>>()
    ))
}

pub fn insert_tries <B, A>
    (ks: List<A>, v: B) -> Rc<dyn Fn(Trie<A, List<B>>) -> Trie<A, List<B>>>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    (({
        let v_cap = v.clone();
        let ks_cap = ks.clone();
        Rc::new(move |a: Trie<A, List<B>>| -> Trie<A, List<B>> {
            update_with_trie(
                ks_cap.clone(),
                (({
                    let v_capa = v_cap.clone();
                    Rc::new(move |aa: Option<List<B>>| -> List<B> {
                        match aa.clone() {
                            Option::None =>
                                List::Cons (v_capa.clone(), Box::new(List::Nil)),
                            Option::Some (ab) =>
                                List::Cons (v_capa.clone(), Box::new(ab.clone())),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<List<B>>) -> List<B>>),
                a.clone()
            )
        })
    }) as Rc<dyn Fn(Trie<A, List<B>>) -> Trie<A, List<B>>>)
}

pub fn inserts_tries <A, B>
    (key: Rc<dyn Fn(A) -> List<B>>) -> Rc<dyn Fn(List<A>,
          Trie<B, List<A>>) -> Trie<B, List<A>>>
where
    A : Clone + 'static,
    B : Clone + Equal + 'static
{
    (({
        let key_cap = key.clone();
        Rc::new(move |a: List<A>, b: Trie<B, List<A>>| -> Trie<B, List<A>> {
            fold(
                (({
                    let key_capa = key_cap.clone();
                    Rc::new(move |v: A, eta_arg: Trie<B,
                List<A>>| -> Trie<B, List<A>> {
                        (*insert_tries((*key_capa)(v.clone()), v.clone()))(eta_arg.clone())
                    })
                }) as Rc<dyn Fn(A, Trie<B, List<A>>) -> Trie<B, List<A>>>),
                a.clone(),
                b.clone()
            )
        })
    }) as Rc<dyn Fn(List<A>, Trie<B, List<A>>) -> Trie<B, List<A>>>)
}

pub fn tries_of_list <A, B>
    (key: Rc<dyn Fn(A) -> List<B>>, vs: List<A>) -> Trie<B, List<A>>
where
    A : Clone + 'static,
    B : Clone + Equal + 'static
{
    (*inserts_tries(key.clone()))(vs.clone(), Trie::Trie (Option::None, Box::new(List::Nil)))
}

pub fn update_with_tries <B, A>
    (ks: List<A>,
      f: Rc<dyn Fn(List<B>) -> List<B>>) -> Rc<dyn Fn(Trie<A,
                     List<B>>) -> Trie<A, List<B>>>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    (({
        let f_cap = f.clone();
        let ks_cap = ks.clone();
        Rc::new(move |a: Trie<A, List<B>>| -> Trie<A, List<B>> {
            update_with_trie(
                ks_cap.clone(),
                (({
                    let f_capa = f_cap.clone();
                    Rc::new(move |aa: Option<List<B>>| -> List<B> {
                        match aa.clone() {
                            Option::None =>
                                (*f_capa)(List::Nil),
                            Option::Some (ab) =>
                                (*f_capa)(ab.clone()),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<List<B>>) -> List<B>>),
                a.clone()
            )
        })
    }) as Rc<dyn Fn(Trie<A, List<B>>) -> Trie<A, List<B>>>)
}
