use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::append;
use crate::List::map_filter;
use crate::List::mapa;
use crate::List::maps;
use crate::Nano_JSON::Json;
use crate::Option::Option;
use crate::String::Literal;

use std::rc::Rc;

pub fn nj_filtera <B, A>
    (key: A, x1: (List<A>, Json<A, B>)) -> List<(List<A>, Json<A, B>)>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (key, x1) {
        (key, (prfx, Json::OBJECT (p0))) =>
            {
                let json = *p0;
                append(map_filter(
                    (({
                        let prfx_cap = prfx.clone();
                        let key_cap = key.clone();
                        Rc::new(move |x: (A, Json<A,
            B>)| -> Option<(List<A>, Json<A, B>)> {
                            if match x.clone() {
                                (k, _) =>
                                    eq(key_cap.clone(), k.clone()),
                                _ =>
                                    panic!("non-exhaustive match")
                            } {
                                Option::Some (
                                    match x.clone() {
                                        (k, a) =>
    (append(prfx_cap.clone(), List::Cons (k.clone(), Box::new(List::Nil))), a.clone()),
_ =>
    panic!("non-exhaustive match")
                                    }
                                )
                            } else {
                                Option::None
                            }
                        })
                    }) as Rc<dyn Fn((A, Json<A,
       B>)) -> Option<(List<A>, Json<A, B>)>>),
                    json.clone()
                ), maps((({
                    let key_cap = key.clone();
                    Rc::new(move |a: (List<A>, Json<A,
              B>)| -> List<(List<A>, Json<A, B>)> {
                        nj_filtera(key_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn((List<A>, Json<A,
         B>)) -> List<(List<A>, Json<A, B>)>>), mapa(
                    (({
                        let prfx_cap = prfx.clone();
                        Rc::new(move |(_, a): (A, Json<A,
                 B>)| -> (List<A>, Json<A, B>) {
                            (prfx_cap.clone(), a.clone())
                        })
                    }) as Rc<dyn Fn((A, Json<A, B>)) -> (List<A>, Json<A, B>)>),
                    json.clone()
                )))
            },
        (key, (prfx, Json::ARRAY (p0))) =>
            {
                let json = *p0;
                maps((({
                    let key_cap = key.clone();
                    Rc::new(move |a: (List<A>, Json<A,
              B>)| -> List<(List<A>, Json<A, B>)> {
                        nj_filtera(key_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn((List<A>, Json<A,
         B>)) -> List<(List<A>, Json<A, B>)>>), mapa((({
                    let prfx_cap = prfx.clone();
                    Rc::new(move |a: Json<A, B>| -> (List<A>, Json<A, B>) {
                        (prfx_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn(Json<A, B>) -> (List<A>, Json<A,
                        B>)>), json.clone()))
            },
        (_, (_, Json::NUMBER (_))) =>
            List::Nil,
        (_, (_, Json::STRING (_))) =>
            List::Nil,
        (_, (_, Json::BOOL (_))) =>
            List::Nil,
        (_, (_, Json::NULL)) =>
            List::Nil,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn nj_filter <B, A>
    (key: A, json: Json<A, B>) -> List<(List<A>, Json<A, B>)>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    nj_filtera(key.clone(), (List::Nil, json.clone()))
}

pub fn nj_update <B, A>
    (f: Rc<dyn Fn(Json<A, B>) -> Json<A, B>>, key: A,
      x2: Json<A, B>) -> Json<A, B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (f, key, x2) {
        (f, key, Json::OBJECT (p0)) =>
            {
                let kjson = *p0;
                Json::OBJECT (Box::new(mapa(
                                    (({
                                        let f_cap = f.clone();
let key_cap = key.clone();
Rc::new(move |(k, json): (A, Json<A, B>)| -> (A, Json<A, B>) {
    if eq(k.clone(), key_cap.clone()) {
        (k.clone(), (*f_cap)(json.clone()))
    } else {
        (k.clone(), nj_update(f_cap.clone(), key_cap.clone(), json.clone()))
    }
})
                                    }) as Rc<dyn Fn((A, Json<A,
                       B>)) -> (A, Json<A, B>)>),
                                    kjson.clone()
                                )))
            },
        (f, key, Json::ARRAY (p0)) =>
            {
                let json = *p0;
                Json::ARRAY (Box::new(mapa((({
                                   let key_cap = key.clone();
                                   let f_cap = f.clone();
                                   Rc::new(move |a: Json<A, B>| -> Json<A, B> {
                                       nj_update(f_cap.clone(), key_cap.clone(), a.clone())
                                   })
                               }) as Rc<dyn Fn(Json<A,
              B>) -> Json<A, B>>), json.clone())))
            },
        (_, _, Json::NUMBER (n)) =>
            Json::NUMBER (n.clone()),
        (_, _, Json::STRING (s)) =>
            Json::STRING (s.clone()),
        (_, _, Json::BOOL (b)) =>
            Json::BOOL (b.clone()),
        (_, _, Json::NULL) =>
            Json::NULL,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn example_literal_literal () -> Json<Literal, BigInt> {
    Json::OBJECT (Box::new(List::Cons ((Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))), Json::OBJECT (Box::new(List::Cons ((Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))), Json::STRING (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Box::new(List::Cons ((Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Json::STRING (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Box::new(List::Cons ((Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))), Json::OBJECT (Box::new(List::Cons ((Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))), Json::ARRAY (Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Json::STRING (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))), Box::new(List::Cons ((Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Json::STRING (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, false, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Json::STRING (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Box::new(List::Cons ((Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Json::STRING (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, false, Box::new(Literal::ZeroLiteral)))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Cons (Json::OBJECT (Box::new(List::Cons ((Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))), Json::STRING (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))), Box::new(List::Cons ((Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Json::STRING (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, false, Box::new(Literal::ZeroLiteral)))))))))))))))))))))), Box::new(List::Nil)))))), Box::new(List::Nil))))))))), Box::new(List::Nil))))), Box::new(List::Nil))))))))), Box::new(List::Cons ((Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))), Json::BOOL (true)), Box::new(List::Cons ((Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))), Json::NUMBER (BigInt::from_bytes_be(Sign::Plus, &[42]))), Box::new(List::Nil))))))))
}
