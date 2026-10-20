use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::suc;
use crate::Basic_BNF_LFPs::size_prod;
use crate::Basic_BNFs::fsts;
use crate::Basic_BNFs::rel_prod;
use crate::Basic_BNFs::snds;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::list_all2;
use crate::List::mapa;
use crate::List::size_list;
use crate::Product_Type::map_prod;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;
use crate::String::Char;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Json<A, B> {
    OBJECT (Box<List<(A, Json<A, B>)>>),
    ARRAY (Box<List<Json<A, B>>>),
    NUMBER (B),
    STRING (A),
    BOOL (bool),
    NULL
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    Json<A, B> {
    fn typerep (x0: Itself<Json<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}

#[derive(Clone)]
pub struct JsonPreJson<A, B, C>(PhantomData<A>, PhantomData<B>, PhantomData<C>);

#[derive(Clone)]
pub struct JsonIITNJson<A, B>(PhantomData<A>, PhantomData<B>);

pub fn example01 () -> Json<List<Char>, BigInt> {
    Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Nil)))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, true, true, false), Box::new(List::Nil)))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Nil)))))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Nil)))))))))))))))), Json::ARRAY (Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Nil)))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Nil))))))))), Box::new(List::Nil))))), Box::new(List::Nil))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, false, true, true, false), Box::new(List::Nil)))))))), Json::BOOL (true)), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Nil)))))))))))), Json::NUMBER (BigInt::from_bytes_be(Sign::Plus, &[42]))), Box::new(List::Nil))))))))
}

pub fn example03 () -> Json<List<Char>, BigInt> {
    Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Nil)))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, true, true, false), Box::new(List::Nil)))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Nil)))))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Nil)))))))))))))))), Json::ARRAY (Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Nil)))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Nil))))))))), Box::new(List::Nil))))), Box::new(List::Nil))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, false, true, true, false), Box::new(List::Nil)))))))), Json::BOOL (true)), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Nil)))))))))))), Json::NUMBER (BigInt::from_bytes_be(Sign::Plus, &[42]))), Box::new(List::Nil))))))))
}

pub fn example04 () -> Json<List<Char>, BigInt> {
    Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Nil)))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, true, true, false), Box::new(List::Nil)))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Nil)))))))))), Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Nil)))))))))))))))), Json::ARRAY (Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Nil)))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Nil)))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, true, true, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Nil)))))))))))), Box::new(List::Cons ((List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, true, false, true, true, false), Box::new(List::Nil)))))))))))))), Json::STRING (List::Cons (Char::Char (true, true, false, false, false, false, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, false, false, false, true, false), Box::new(List::Cons (Char::Char (true, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, false, true, false, true, false, false), Box::new(List::Cons (Char::Char (true, false, false, true, false, true, false, false), Box::new(List::Nil)))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Nil))))))))), Box::new(List::Nil))))), Box::new(List::Nil))))))))), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, true, true, false, false, true, true, false), Box::new(List::Nil)))))))), Json::BOOL (true)), Box::new(List::Cons ((List::Cons (Char::Char (false, true, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, true, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, true, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, false, true, true, false), Box::new(List::Cons (Char::Char (true, false, true, false, false, true, true, false), Box::new(List::Cons (Char::Char (false, true, false, false, true, true, true, false), Box::new(List::Nil)))))))))))), Json::NUMBER (BigInt::from_bytes_be(Sign::Plus, &[42]))), Box::new(List::Nil))))))))
}

pub fn map_json <D, B, C, A>
    (f1: Rc<dyn Fn(A) -> B>, f2: Rc<dyn Fn(C) -> D>,
      x2: Json<A, C>) -> Json<B, D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (f1, f2, x2) {
        (f1, f2, Json::OBJECT (p0)) =>
            {
                let x1 = *p0;
                Json::OBJECT (Box::new(mapa((({
                                    let f2_cap = f2.clone();
                                    let f1_cap = f1.clone();
                                    Rc::new(move |a: (A, Json<A,
                        C>)| -> (B, Json<B, D>) {
                                        map_prod(f1_cap.clone(), (({
    let f2_capa = f2_cap.clone();
    let f1_capa = f1_cap.clone();
    Rc::new(move |aa: Json<A, C>| -> Json<B, D> {
        map_json(f1_capa.clone(), f2_capa.clone(), aa.clone())
    })
}) as Rc<dyn Fn(Json<A, C>) -> Json<B, D>>), a.clone())
                                    })
                                }) as Rc<dyn Fn((A, Json<A,
                   C>)) -> (B, Json<B, D>)>), x1.clone())))
            },
        (f1, f2, Json::ARRAY (p0)) =>
            {
                let x2 = *p0;
                Json::ARRAY (Box::new(mapa((({
                                   let f2_cap = f2.clone();
                                   let f1_cap = f1.clone();
                                   Rc::new(move |a: Json<A, C>| -> Json<B, D> {
                                       map_json(f1_cap.clone(), f2_cap.clone(), a.clone())
                                   })
                               }) as Rc<dyn Fn(Json<A,
              C>) -> Json<B, D>>), x2.clone())))
            },
        (_, f2, Json::NUMBER (x3)) =>
            Json::NUMBER ((*f2)(x3.clone())),
        (f1, _, Json::STRING (x4)) =>
            Json::STRING ((*f1)(x4.clone())),
        (_, _, Json::BOOL (x5)) =>
            Json::BOOL (x5.clone()),
        (_, _, Json::NULL) =>
            Json::NULL,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rec_json <C, B, A>
    (f1: Rc<dyn Fn(List<(A, (Json<A, B>, C))>) -> C>,
      f2: Rc<dyn Fn(List<(Json<A, B>, C)>) -> C>, f3: Rc<dyn Fn(B) -> C>,
      f4: Rc<dyn Fn(A) -> C>, f5: Rc<dyn Fn(bool) -> C>, f6: C,
      x6: Json<A, B>) -> C
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f1, f2, f3, f4, f5, f6, x6) {
        (f1, f2, f3, f4, f5, f6, Json::OBJECT (p0)) =>
            {
                let x1 = *p0;
                (*f1)(mapa((({
                    let f6_cap = f6.clone();
                    let f5_cap = f5.clone();
                    let f4_cap = f4.clone();
                    let f3_cap = f3.clone();
                    let f2_cap = f2.clone();
                    let f1_cap = f1.clone();
                    Rc::new(move |a: (A, Json<A, B>)| -> (A, (Json<A, B>, C)) {
                        map_prod(
                            ((Rc::new(move |aa: A| -> A {
                                id(aa.clone())
                            })) as Rc<dyn Fn(A) -> A>),
                            (({
                                let f6_capa = f6_cap.clone();
                                let f5_capa = f5_cap.clone();
                                let f4_capa = f4_cap.clone();
                                let f3_capa = f3_cap.clone();
                                let f2_capa = f2_cap.clone();
                                let f1_capa = f1_cap.clone();
                                Rc::new(move |json: Json<A,
                   B>| -> (Json<A, B>, C) {
                                    (json.clone(), rec_json(f1_capa.clone(), f2_capa.clone(), f3_capa.clone(), f4_capa.clone(), f5_capa.clone(), f6_capa.clone(), json.clone()))
                                })
                            }) as Rc<dyn Fn(Json<A, B>) -> (Json<A, B>, C)>),
                            a.clone()
                        )
                    })
                }) as Rc<dyn Fn((A, Json<A,
   B>)) -> (A, (Json<A, B>, C))>), x1.clone()))
            },
        (f1, f2, f3, f4, f5, f6, Json::ARRAY (p0)) =>
            {
                let x2 = *p0;
                (*f2)(mapa(
                    (({
                        let f6_cap = f6.clone();
                        let f5_cap = f5.clone();
                        let f4_cap = f4.clone();
                        let f3_cap = f3.clone();
                        let f2_cap = f2.clone();
                        let f1_cap = f1.clone();
                        Rc::new(move |json: Json<A, B>| -> (Json<A, B>, C) {
                            (json.clone(), rec_json(f1_cap.clone(), f2_cap.clone(), f3_cap.clone(), f4_cap.clone(), f5_cap.clone(), f6_cap.clone(), json.clone()))
                        })
                    }) as Rc<dyn Fn(Json<A, B>) -> (Json<A, B>, C)>),
                    x2.clone()
                ))
            },
        (_, _, f3, _, _, _, Json::NUMBER (x3)) =>
            (*f3)(x3.clone()),
        (_, _, _, f4, _, _, Json::STRING (x4)) =>
            (*f4)(x4.clone()),
        (_, _, _, _, f5, _, Json::BOOL (x5)) =>
            (*f5)(x5.clone()),
        (_, _, _, _, _, f6, Json::NULL) =>
            f6.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_json <D, B, C, A>
    (r1: Rc<dyn Fn(A, B) -> bool>, r2: Rc<dyn Fn(C, D) -> bool>, x2: Json<A, C>,
      x3: Json<B, D>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (r1, r2, x2, x3) {
        (_, _, Json::OBJECT (_), Json::ARRAY (_)) =>
            false,
        (_, _, Json::ARRAY (_), Json::OBJECT (_)) =>
            false,
        (_, _, Json::OBJECT (_), Json::NUMBER (_)) =>
            false,
        (_, _, Json::NUMBER (_), Json::OBJECT (_)) =>
            false,
        (_, _, Json::OBJECT (_), Json::STRING (_)) =>
            false,
        (_, _, Json::STRING (_), Json::OBJECT (_)) =>
            false,
        (_, _, Json::OBJECT (_), Json::BOOL (_)) =>
            false,
        (_, _, Json::BOOL (_), Json::OBJECT (_)) =>
            false,
        (_, _, Json::OBJECT (_), Json::NULL) =>
            false,
        (_, _, Json::NULL, Json::OBJECT (_)) =>
            false,
        (_, _, Json::ARRAY (_), Json::NUMBER (_)) =>
            false,
        (_, _, Json::NUMBER (_), Json::ARRAY (_)) =>
            false,
        (_, _, Json::ARRAY (_), Json::STRING (_)) =>
            false,
        (_, _, Json::STRING (_), Json::ARRAY (_)) =>
            false,
        (_, _, Json::ARRAY (_), Json::BOOL (_)) =>
            false,
        (_, _, Json::BOOL (_), Json::ARRAY (_)) =>
            false,
        (_, _, Json::ARRAY (_), Json::NULL) =>
            false,
        (_, _, Json::NULL, Json::ARRAY (_)) =>
            false,
        (_, _, Json::NUMBER (_), Json::STRING (_)) =>
            false,
        (_, _, Json::STRING (_), Json::NUMBER (_)) =>
            false,
        (_, _, Json::NUMBER (_), Json::BOOL (_)) =>
            false,
        (_, _, Json::BOOL (_), Json::NUMBER (_)) =>
            false,
        (_, _, Json::NUMBER (_), Json::NULL) =>
            false,
        (_, _, Json::NULL, Json::NUMBER (_)) =>
            false,
        (_, _, Json::STRING (_), Json::BOOL (_)) =>
            false,
        (_, _, Json::BOOL (_), Json::STRING (_)) =>
            false,
        (_, _, Json::STRING (_), Json::NULL) =>
            false,
        (_, _, Json::NULL, Json::STRING (_)) =>
            false,
        (_, _, Json::BOOL (_), Json::NULL) =>
            false,
        (_, _, Json::NULL, Json::BOOL (_)) =>
            false,
        (r1, r2, Json::OBJECT (p0), Json::OBJECT (p1)) =>
            {
                let x1 = *p0;
                let y1 = *p1;
                list_all2((({
                    let r2_cap = r2.clone();
                    let r1_cap = r1.clone();
                    Rc::new(move |a: (A, Json<A,
        C>), b: (B, Json<B, D>)| -> bool {
                        rel_prod(r1_cap.clone(), (({
                            let r2_capa = r2_cap.clone();
                            let r1_capa = r1_cap.clone();
                            Rc::new(move |aa: Json<A,
             C>, ba: Json<B, D>| -> bool {
                                rel_json(r1_capa.clone(), r2_capa.clone(), aa.clone(), ba.clone())
                            })
                        }) as Rc<dyn Fn(Json<A, C>,
 Json<B, D>) -> bool>), a.clone(), b.clone())
                    })
                }) as Rc<dyn Fn((A, Json<A, C>),
                                 (B, Json<B,
    D>)) -> bool>), x1.clone(), y1.clone())
            },
        (r1, r2, Json::ARRAY (p0), Json::ARRAY (p1)) =>
            {
                let x2 = *p0;
                let y2 = *p1;
                list_all2((({
                    let r2_cap = r2.clone();
                    let r1_cap = r1.clone();
                    Rc::new(move |a: Json<A, C>, b: Json<B, D>| -> bool {
                        rel_json(r1_cap.clone(), r2_cap.clone(), a.clone(), b.clone())
                    })
                }) as Rc<dyn Fn(Json<A, C>,
                                 Json<B, D>) -> bool>), x2.clone(), y2.clone())
            },
        (_, r2, Json::NUMBER (x3), Json::NUMBER (y3)) =>
            (*r2)(x3.clone(), y3.clone()),
        (r1, _, Json::STRING (x4), Json::STRING (y4)) =>
            (*r1)(x4.clone(), y4.clone()),
        (_, _, Json::BOOL (x5), Json::BOOL (y5)) =>
            <bool as Equal>::equal(x5.clone(), y5.clone()),
        (_, _, Json::NULL, Json::NULL) =>
            true,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set1_json <A, B> (x0: Json<A, B>) -> Set<A>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        Json::OBJECT (p0) =>
            {
                let x1 = *p0;
                crate::Complete_Lattices::sup_set(image(
                    ((Rc::new(move |uu: (A, Json<A, B>)| -> Set<A> {
                        crate::Set::sup_set((*fsts())(uu.clone()), crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Json<A,
             B>| -> Set<A> {
                            set1_json(a.clone())
                        })) as Rc<dyn Fn(Json<A,
        B>) -> Set<A>>), (*snds())(uu.clone()))))
                    })) as Rc<dyn Fn((A, Json<A, B>)) -> Set<A>>),
                    Set::Set (x1.clone())
                ))
            },
        Json::ARRAY (p0) =>
            {
                let x2 = *p0;
                crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Json<A,
  B>| -> Set<A> {
                    set1_json(a.clone())
                })) as Rc<dyn Fn(Json<A,
B>) -> Set<A>>), Set::Set (x2.clone())))
            },
        Json::NUMBER (_) =>
            bot_set::<A>(),
        Json::STRING (x4) =>
            insert(x4.clone(), bot_set::<A>()),
        Json::BOOL (_) =>
            bot_set::<A>(),
        Json::NULL =>
            bot_set::<A>(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set2_json <B, A> (x0: Json<A, B>) -> Set<B>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        Json::OBJECT (p0) =>
            {
                let x1 = *p0;
                crate::Complete_Lattices::sup_set(image(
                    ((Rc::new(move |uu: (A, Json<A, B>)| -> Set<B> {
                        crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Json<A,
          B>| -> Set<B> {
                            set2_json(a.clone())
                        })) as Rc<dyn Fn(Json<A,
        B>) -> Set<B>>), (*snds())(uu.clone())))
                    })) as Rc<dyn Fn((A, Json<A, B>)) -> Set<B>>),
                    Set::Set (x1.clone())
                ))
            },
        Json::ARRAY (p0) =>
            {
                let x2 = *p0;
                crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Json<A,
  B>| -> Set<B> {
                    set2_json(a.clone())
                })) as Rc<dyn Fn(Json<A,
B>) -> Set<B>>), Set::Set (x2.clone())))
            },
        Json::NUMBER (x3) =>
            insert(x3.clone(), bot_set::<B>()),
        Json::STRING (_) =>
            bot_set::<B>(),
        Json::BOOL (_) =>
            bot_set::<B>(),
        Json::NULL =>
            bot_set::<B>(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_json <B, A>
    (xa: Rc<dyn Fn(A) -> BigInt>, x: Rc<dyn Fn(B) -> BigInt>,
      xb2: Json<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (xa, x, xb2) {
        (xa, x, Json::OBJECT (p0)) =>
            {
                let x1 = *p0;
                size_list((({
                      let x_cap = x.clone();
                      let xa_cap = xa.clone();
                      Rc::new(move |a: (A, Json<A, B>)| -> BigInt {
                          size_prod(xa_cap.clone(), (({
                              let x_capa = x_cap.clone();
                              let xa_capa = xa_cap.clone();
                              Rc::new(move |aa: Json<A, B>| -> BigInt {
                                  size_json(xa_capa.clone(), x_capa.clone(), aa.clone())
                              })
                          }) as Rc<dyn Fn(Json<A, B>) -> BigInt>), a.clone())
                      })
                  }) as Rc<dyn Fn((A, Json<A, B>)) -> BigInt>), x1.clone()) +
                  suc(BigInt::ZERO)
            },
        (xa, x, Json::ARRAY (p0)) =>
            {
                let x2 = *p0;
                size_list((({
                      let x_cap = x.clone();
                      let xa_cap = xa.clone();
                      Rc::new(move |a: Json<A, B>| -> BigInt {
                          size_json(xa_cap.clone(), x_cap.clone(), a.clone())
                      })
                  }) as Rc<dyn Fn(Json<A, B>) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        (_, x, Json::NUMBER (x3)) =>
            (*x)(x3.clone()) + suc(BigInt::ZERO),
        (xa, _, Json::STRING (x4)) =>
            (*xa)(x4.clone()) + suc(BigInt::ZERO),
        (_, _, Json::BOOL (_)) =>
            suc(BigInt::ZERO),
        (_, _, Json::NULL) =>
            suc(BigInt::ZERO),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_jsona <B, A> (x0: Json<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Json::OBJECT (p0) =>
            {
                let x1 = *p0;
                size_list(((Rc::new(move |a: (A, Json<A, B>)| -> BigInt {
                      size_prod(
                          ((Rc::new(move |_: A| -> BigInt {
                              BigInt::ZERO
                          })) as Rc<dyn Fn(A) -> BigInt>),
                          ((Rc::new(move |aa: Json<A, B>| -> BigInt {
                              size_jsona(aa.clone())
                          })) as Rc<dyn Fn(Json<A, B>) -> BigInt>),
                          a.clone()
                      )
                  })) as Rc<dyn Fn((A, Json<A, B>)) -> BigInt>), x1.clone()) +
                  suc(BigInt::ZERO)
            },
        Json::ARRAY (p0) =>
            {
                let x2 = *p0;
                size_list(((Rc::new(move |a: Json<A, B>| -> BigInt {
                      size_jsona(a.clone())
                  })) as Rc<dyn Fn(Json<A, B>) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        Json::NUMBER (_) =>
            suc(BigInt::ZERO),
        Json::STRING (_) =>
            suc(BigInt::ZERO),
        Json::BOOL (_) =>
            suc(BigInt::ZERO),
        Json::NULL =>
            suc(BigInt::ZERO),
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static, 
       C : Clone + Typerep + 'static>
    Typerep for JsonPreJson<A, B, C> {
    fn typerep (x0: Itself<JsonPreJson<A, B, C>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (<C as Typerep>::typerep(Itself::Type (PhantomData::<C>)), Box::new(List::Nil))))))))
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    JsonIITNJson<A, B> {
    fn typerep (x0: Itself<JsonIITNJson<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}
