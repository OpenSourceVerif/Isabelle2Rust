use std::rc::Rc;

pub fn whilea <A> (b: Rc<dyn Fn(A) -> bool>, c: Rc<dyn Fn(A) -> A>, s: A) -> A
where
    A : Clone + 'static
{
    if (*b)(s.clone()) {
        whilea(b.clone(), c.clone(), (*c)(s.clone()))
    } else {
        s.clone()
    }
}
