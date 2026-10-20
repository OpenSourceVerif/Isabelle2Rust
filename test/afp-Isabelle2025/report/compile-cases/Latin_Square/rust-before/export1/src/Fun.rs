use crate::HOL::Equal;
use crate::HOL::eq;
use crate::HOL::implies;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::image;

use std::rc::Rc;

pub fn id <A> (x: A) -> A
where
    A : Clone + 'static
{
    (*Rc::new(move |xa: A| {
        xa.clone()
    }))(x.clone())
}

pub fn comp <B, C, A>
    (f: Rc<dyn Fn(A) -> B>, g: Rc<dyn Fn(C) -> A>) -> Rc<dyn Fn(C) -> B>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    let g_cap = g.clone();
    let f_cap = f.clone();
    Rc::new(move |x: C| -> B {
        (*f_cap)((*g_cap)(x.clone()))
    })
}

pub fn inj_on <A, B> (f: Rc<dyn Fn(A) -> B>, a: Set<A>) -> bool
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    ball(
        a.clone(),
        (({
            let f_cap = f.clone();
            let a_cap = a.clone();
            Rc::new(move |x: A| -> bool {
                ball(
                    a_cap.clone(),
                    (({
                        let x_cap = x.clone();
                        let f_capa = f_cap.clone();
                        Rc::new(move |y: A| -> bool {
                            implies(eq((*f_capa)(x_cap.clone()), (*f_capa)(y.clone())), eq(x_cap.clone(), y.clone()))
                        })
                    }) as Rc<dyn Fn(A) -> bool>)
                )
            })
        }) as Rc<dyn Fn(A) -> bool>)
    )
}

pub fn bij_betw <B, A> (f: Rc<dyn Fn(A) -> B>, a: Set<A>, b: Set<B>) -> bool
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    inj_on(f.clone(), a.clone()) && eq(image(f.clone(), a.clone()), b.clone())
}
