#[derive(Clone)]
pub enum Literal {
    ZeroLiteral,
    Literal (bool, bool, bool, bool, bool, bool, bool, Box<Literal>)
}
