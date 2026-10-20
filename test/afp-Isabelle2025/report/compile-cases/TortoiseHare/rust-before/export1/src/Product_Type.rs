use std::rc::Rc;

#[derive(Clone)]
pub enum Unit {
    Unity
}

pub fn apsnd <B, C, A> (f: Rc<dyn Fn(A) -> B>, x1: (C, A)) -> (C, B)
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, (x, y)) =>
            (x.clone(), (*f)(y.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn scomp <D, A, C, B>
    (f: Rc<dyn Fn(A) -> (B, C)>, g: Rc<dyn Fn(B, C) -> D>) -> Rc<dyn Fn(A) -> D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    let g_cap = g.clone();
    let f_cap = f.clone();
    Rc::new(move |x: A| -> D {
        match (*f_cap)(x.clone()) {
            (a, b) =>
                (*g_cap)(a.clone(), b.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    })
}

pub fn fst <A, B> (x0: (A, B)) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (x1, _) =>
            x1.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn snd <B, A> (x0: (A, B)) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (_, x2) =>
            x2.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}
