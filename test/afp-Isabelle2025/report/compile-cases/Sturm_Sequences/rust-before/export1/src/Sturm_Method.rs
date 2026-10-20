pub fn pr_tag <A> (x: A) -> A
where
    A : Clone + 'static
{
    x.clone()
}
