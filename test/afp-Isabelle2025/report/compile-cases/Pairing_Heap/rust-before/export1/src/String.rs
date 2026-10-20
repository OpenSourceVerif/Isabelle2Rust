impl crate::Arith::Zero for Literal {
    fn zero () -> Self { Literal::ZeroLiteral }
}

#[derive(Clone)]
pub enum Literal {
    ZeroLiteral,
    Literal (bool, bool, bool, bool, bool, bool, bool, Box<Literal>)
}
