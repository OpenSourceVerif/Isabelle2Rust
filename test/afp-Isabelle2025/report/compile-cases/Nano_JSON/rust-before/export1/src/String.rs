#[derive(Clone)]
pub enum Char {
    Char (bool, bool, bool, bool, bool, bool, bool, bool)
}

#[derive(Clone)]
pub enum Literal {
    ZeroLiteral,
    Literal (bool, bool, bool, bool, bool, bool, bool, Box<Literal>)
}
