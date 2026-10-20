use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::suc;
use crate::FJDefs::ClassDefExt;
use crate::FJDefs::ConstructorDefExt;
use crate::FJDefs::Exp;
use crate::FJDefs::MethodDefExt;
use crate::FJDefs::VarDefExt;
use crate::FJDefs::c_constructor;
use crate::FJDefs::c_fields;
use crate::FJDefs::c_methods;
use crate::FJDefs::c_name;
use crate::FJDefs::c_super;
use crate::FJDefs::k_inits;
use crate::FJDefs::k_name;
use crate::FJDefs::k_params;
use crate::FJDefs::k_super;
use crate::FJDefs::lookup;
use crate::FJDefs::lookup2;
use crate::FJDefs::m_body;
use crate::FJDefs::m_name;
use crate::FJDefs::m_params;
use crate::FJDefs::m_return;
use crate::FJDefs::objecta;
use crate::FJDefs::substs;
use crate::FJDefs::this;
use crate::FJDefs::var_defs_names;
use crate::FJDefs::var_defs_types;
use crate::FJDefs::vd_name;
use crate::FJDefs::vd_type;
use crate::Fun::fun_upd;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::size_lista;
use crate::Map::map_upds;
use crate::Option::Option;
use crate::Predicate::Pred;
use crate::Predicate::bind;
use crate::Predicate::bot_pred;
use crate::Predicate::holds;
use crate::Predicate::if_pred;
use crate::Predicate::not_pred;
use crate::Predicate::single;
use crate::Predicate::sup_pred;
use crate::Product_Type::Unit;

use std::rc::Rc;

pub fn append_i_i_i <A> (xa: List<A>, xb: List<A>, xc: List<A>) -> Pred<Unit>
where
    A : Clone + Equal + 'static
{
    sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (List<A>, (List<A>, List<A>))| -> Pred<Unit> {
            match a.clone() {
                (List::Nil, (xs, xsa)) =>
                    if <List<A> as Equal>::equal(xs.clone(), xsa.clone()) {
                        single(Unit::Unity)
                    } else {
                        bot_pred::<Unit>()
                    },
                (List::Cons (_, _), _) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, (List<A>, List<A>))) -> Pred<Unit>>)
    ), bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (List<A>, (List<A>, List<A>))| -> Pred<Unit> {
            match a.clone() {
                (List::Nil, _) =>
                    bot_pred::<Unit>(),
                (List::Cons (_, _), (_, List::Nil)) =>
                    bot_pred::<Unit>(),
                (List::Cons (x, p0), (ys, List::Cons (xaa, p1))) =>
                    {
                        let xs = *p0;
                        let zs = *p1;
                        if eq(x.clone(), xaa.clone()) {
                            bind(
                                append_i_i_i(xs.clone(), ys.clone(), zs.clone()),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, (List<A>, List<A>))) -> Pred<Unit>>)
    ))
}

pub fn append <A> (x1: List<A>, x2: List<A>, x3: List<A>) -> bool
where
    A : Clone + Equal + 'static
{
    holds(append_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn eq_i_i <A> (xa: A, xb: A) -> Pred<Unit>
where
    A : Clone + Equal + 'static
{
    bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |(x, xaa): (A, A)| -> Pred<Unit> {
            if eq(x.clone(), xaa.clone()) {
                single(Unit::Unity)
            } else {
                bot_pred::<Unit>()
            }
        })) as Rc<dyn Fn((A, A)) -> Pred<Unit>>)
    )
}

pub fn eq_i_o <A> (xa: A) -> Pred<A>
where
    A : Clone + 'static
{
    bind(single(xa.clone()), ((Rc::new(move |a: A| -> Pred<A> {
        single(a.clone())
    })) as Rc<dyn Fn(A) -> Pred<A>>))
}

pub fn eq_o_i <A> (xa: A) -> Pred<A>
where
    A : Clone + 'static
{
    bind(single(xa.clone()), ((Rc::new(move |a: A| -> Pred<A> {
        single(a.clone())
    })) as Rc<dyn Fn(A) -> Pred<A>>))
}

pub fn supertypes_of
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xa: BigInt) -> Pred<BigInt> {
    sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(_, a): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)| -> Pred<BigInt> {
            single(a.clone())
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(ct, c): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)| -> Pred<BigInt> {
            bind(
                supertypes_of(ct.clone(), c.clone()),
                (({
                    let ct_cap = ct.clone();
                    Rc::new(move |xb: BigInt| -> Pred<BigInt> {
                        bind(supertypes_of(ct_cap.clone(), xb.clone()), ((Rc::new(move |a: BigInt| -> Pred<BigInt> {
                            single(a.clone())
                        })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>))
                    })
                }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)) -> Pred<BigInt>>)
    ), bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(ct, c): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)| -> Pred<BigInt> {
            bind(
                eq_i_o((*ct)(c.clone())),
                ((Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<BigInt> {
                    match a.clone() {
                        Option::None =>
                            bot_pred::<BigInt>(),
                        Option::Some (cDef) =>
                            bind(eq_i_o(c_super(cDef.clone())), ((Rc::new(move |aa: BigInt| -> Pred<BigInt> {
                                single(aa.clone())
                            })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)),
                        _ =>
                            panic!("non-exhaustive match")
                    }
                })) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<BigInt>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)) -> Pred<BigInt>>)
    )))
}

pub fn subtyping_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt,
      xb: BigInt) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(_, (c, ca)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<Unit> {
            if c.clone() == ca.clone() {
                single(Unit::Unity)
            } else {
                bot_pred::<Unit>()
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (c, e)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<Unit> {
            bind(
                supertypes_of(ct.clone(), c.clone()),
                (({
                    let e_cap = e.clone();
                    let ct_cap = ct.clone();
                    Rc::new(move |xc: BigInt| -> Pred<Unit> {
                        bind(
                            subtyping_i_i_i(ct_cap.clone(), xc.clone(), e_cap.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (c, d)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let d_cap = d.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(c_super(cDef.clone()), d_cap.clone()),
                                    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                        single(Unit::Unity)
                                    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<Unit>>)
    )))
}

pub fn mbody_i_i_i_o_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt,
      xb: BigInt) -> Pred<(List<BigInt>, Exp)> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (m, c)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<(List<BigInt>, Exp)> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<(List<BigInt>, Exp)> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<(List<BigInt>, Exp)>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    ((Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<(List<BigInt>, Exp)> {
                                        match aa.clone() {
    Option::None =>
        bot_pred::<(List<BigInt>, Exp)>(),
    Option::Some (mDef) =>
        bind(
            eq_i_o(var_defs_names(m_params(mDef.clone()))),
            (({
                let mDef_cap = mDef.clone();
                Rc::new(move |xc: List<BigInt>| -> Pred<(List<BigInt>, Exp)> {
                    bind(
                        eq_i_o(m_body(mDef_cap.clone())),
                        (({
                            let x_cap = xc.clone();
                            Rc::new(move |xaa: Exp| -> Pred<(List<BigInt>, Exp)> {
                                single((x_cap.clone(), xaa.clone()))
                            })
                        }) as Rc<dyn Fn(Exp) -> Pred<(List<BigInt>, Exp)>>)
                    )
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Pred<(List<BigInt>, Exp)>>)
        ),
    _ =>
        panic!("non-exhaustive match")
}
                                    })) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<(List<BigInt>, Exp)>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<(List<BigInt>, Exp)>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<(List<BigInt>, Exp)>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (m, c)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<(List<BigInt>, Exp)> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<(List<BigInt>, Exp)> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<(List<BigInt>, Exp)>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<(List<BigInt>, Exp)> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xc: BigInt| -> Pred<(List<BigInt>, Exp)> {
                bind(
                    mbody_i_i_i_o_o(ct_capb.clone(), m_capb.clone(), xc.clone()),
                    ((Rc::new(move |(xs, e): (List<BigInt>, Exp)| -> Pred<(List<BigInt>, Exp)> {
                        single((xs.clone(), e.clone()))
                    })) as Rc<dyn Fn((List<BigInt>, Exp)) -> Pred<(List<BigInt>, Exp)>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<(List<BigInt>, Exp)>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<(List<BigInt>, Exp)>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<(List<BigInt>, Exp)>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<(List<BigInt>, Exp)>>)
    ))
}

pub fn fields_i_i_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xa: BigInt) -> Pred<List<VarDefExt<Unit>>> {
    sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(_, xb): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)| -> Pred<List<VarDefExt<Unit>>> {
            if xb.clone() == objecta() {
                single(List::Nil)
            } else {
                bot_pred::<List<VarDefExt<Unit>>>()
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)) -> Pred<List<VarDefExt<Unit>>>>)
    ), bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(ct, c): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)| -> Pred<List<VarDefExt<Unit>>> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let ct_cap = ct.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<List<VarDefExt<Unit>>> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<List<VarDefExt<Unit>>>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(c_super(cDef.clone())),
                                    (({
                                        let cDef_cap = cDef.clone();
let ct_capa = ct_cap.clone();
Rc::new(move |xb: BigInt| -> Pred<List<VarDefExt<Unit>>> {
    bind(
        fields_i_i_o(ct_capa.clone(), xb.clone()),
        (({
            let cDef_capa = cDef_cap.clone();
            Rc::new(move |xc: List<VarDefExt<Unit>>| -> Pred<List<VarDefExt<Unit>>> {
                bind(
                    eq_i_o(c_fields(cDef_capa.clone())),
                    (({
                        let x_cap = xc.clone();
                        Rc::new(move |xaa: List<VarDefExt<Unit>>| -> Pred<List<VarDefExt<Unit>>> {
                            bind(eq_o_i(crate::List::append(x_cap.clone(), xaa.clone())), ((Rc::new(move |aa: List<VarDefExt<Unit>>| -> Pred<List<VarDefExt<Unit>>> {
                                single(aa.clone())
                            })) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<List<VarDefExt<Unit>>>>))
                        })
                    }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<List<VarDefExt<Unit>>>>)
                )
            })
        }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<List<VarDefExt<Unit>>>>)
    )
})
                                    }) as Rc<dyn Fn(BigInt) -> Pred<List<VarDefExt<Unit>>>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<List<VarDefExt<Unit>>>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, BigInt)) -> Pred<List<VarDefExt<Unit>>>>)
    ))
}

pub fn append_o_o_i <A> (xa: List<A>) -> Pred<(List<A>, List<A>)>
where
    A : Clone + 'static
{
    sup_pred(bind(
        single(xa.clone()),
        ((Rc::new(move |x: List<A>| -> Pred<(List<A>, List<A>)> {
            single((List::Nil, x.clone()))
        })) as Rc<dyn Fn(List<A>) -> Pred<(List<A>, List<A>)>>)
    ), bind(
        single(xa.clone()),
        ((Rc::new(move |a: List<A>| -> Pred<(List<A>, List<A>)> {
            match a.clone() {
                List::Nil =>
                    bot_pred::<(List<A>, List<A>)>(),
                List::Cons (x, p0) =>
                    {
                        let zs = *p0;
                        bind(
                            append_o_o_i(zs.clone()),
                            (({
                                let x_cap = x.clone();
                                Rc::new(move |(xs, ys): (List<A>, List<A>)| -> Pred<(List<A>, List<A>)> {
                                    single((List::Cons (x_cap.clone(), Box::new(xs.clone())), ys.clone()))
                                })
                            }) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<(List<A>, List<A>)>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn(List<A>) -> Pred<(List<A>, List<A>)>>)
    ))
}

pub fn append_i_i_o <A> (xa: List<A>, xb: List<A>) -> Pred<List<A>>
where
    A : Clone + 'static
{
    sup_pred(bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |a: (List<A>, List<A>)| -> Pred<List<A>> {
            match a.clone() {
                (List::Nil, xs) =>
                    single(xs.clone()),
                (List::Cons (_, _), _) =>
                    bot_pred::<List<A>>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ), bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |a: (List<A>, List<A>)| -> Pred<List<A>> {
            match a.clone() {
                (List::Nil, _) =>
                    bot_pred::<List<A>>(),
                (List::Cons (x, p0), ys) =>
                    {
                        let xs = *p0;
                        bind(
                            append_i_i_o(xs.clone(), ys.clone()),
                            (({
                                let x_cap = x.clone();
                                Rc::new(move |xaa: List<A>| -> Pred<List<A>> {
                                    single(List::Cons (x_cap.clone(), Box::new(xaa.clone())))
                                })
                            }) as Rc<dyn Fn(List<A>) -> Pred<List<A>>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ))
}

pub fn reduce
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: Exp) -> Pred<Exp> {
    sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        Exp::Var (_) =>
                            bot_pred::<Exp>(),
                        Exp::FieldProj (p1, fi) =>
                            match *p1 {
                                Exp::Var (_) =>
                                    bot_pred::<Exp>(),
                                Exp::FieldProj (_, _) =>
                                    bot_pred::<Exp>(),
                                Exp::MethodInvk (_, _, _) =>
                                    bot_pred::<Exp>(),
                                Exp::New (c, p2a) =>
                                    {
                                        let es = *p2a;
bind(
    fields_i_i_o(ct.clone(), c.clone()),
    (({
        let fi_cap = fi.clone();
        let es_cap = es.clone();
        Rc::new(move |xb: List<VarDefExt<Unit>>| -> Pred<Exp> {
            bind(
                eq_i_o(lookup2(
                    xb.clone(),
                    es_cap.clone(),
                    (({
                        let fi_capa = fi_cap.clone();
                        Rc::new(move |fd: VarDefExt<Unit>| -> bool {
                            vd_name(fd.clone()) == fi_capa.clone()
                        })
                    }) as Rc<dyn Fn(VarDefExt<Unit>) -> bool>)
                )),
                ((Rc::new(move |aa: Option<Exp>| -> Pred<Exp> {
                    match aa.clone() {
                        Option::None =>
                            bot_pred::<Exp>(),
                        Option::Some (ab) =>
                            single(ab.clone()),
                        _ =>
                            panic!("non-exhaustive match")
                    }
                })) as Rc<dyn Fn(Option<Exp>) -> Pred<Exp>>)
            )
        })
    }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Exp>>)
)
                                    },
                                Exp::Cast (_, _) =>
                                    bot_pred::<Exp>(),
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        Exp::MethodInvk (_, _, _) =>
                            bot_pred::<Exp>(),
                        Exp::New (_, _) =>
                            bot_pred::<Exp>(),
                        Exp::Cast (_, _) =>
                            bot_pred::<Exp>(),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        Exp::Var (_) =>
                            bot_pred::<Exp>(),
                        Exp::FieldProj (_, _) =>
                            bot_pred::<Exp>(),
                        Exp::MethodInvk (p1, m, p1b) =>
                            match *p1 {
                                Exp::Var (_) =>
                                    bot_pred::<Exp>(),
                                Exp::FieldProj (_, _) =>
                                    bot_pred::<Exp>(),
                                Exp::MethodInvk (_, _, _) =>
                                    bot_pred::<Exp>(),
                                Exp::New (c, p2a) =>
                                    {
                                        let es = *p2a;
let ds = *p1b;
bind(
    mbody_i_i_i_o_o(ct.clone(), m.clone(), c.clone()),
    (({
        let es_cap = es.clone();
        let c_cap = c.clone();
        let ds_cap = ds.clone();
        Rc::new(move |(xs, e0): (List<BigInt>, Exp)| -> Pred<Exp> {
            bind(eq_i_o(substs((({
                let es_capa = es_cap.clone();
                let c_capa = c_cap.clone();
                let ds_capa = ds_cap.clone();
                let xs_cap = xs.clone();
                Rc::new(move |aa: BigInt| -> Option<Exp> {
                    (*fun_upd((({
                        let ds_capb = ds_capa.clone();
                        let xs_capa = xs_cap.clone();
                        Rc::new(move |ab: BigInt| -> Option<Exp> {
                            (*map_upds(
                                ((Rc::new(move |_: BigInt| -> Option<Exp> {
                                    Option::None
                                })) as Rc<dyn Fn(BigInt) -> Option<Exp>>),
                                xs_capa.clone(),
                                ds_capb.clone()
                            ))(ab.clone())
                        })
                    }) as Rc<dyn Fn(BigInt) -> Option<Exp>>), this(), Option::Some (Exp::New (c_capa.clone(), Box::new(es_capa.clone())))))(aa.clone())
                })
            }) as Rc<dyn Fn(BigInt) -> Option<Exp>>), e0.clone())), ((Rc::new(move |aa: Exp| -> Pred<Exp> {
                single(aa.clone())
            })) as Rc<dyn Fn(Exp) -> Pred<Exp>>))
        })
    }) as Rc<dyn Fn((List<BigInt>, Exp)) -> Pred<Exp>>)
)
                                    },
                                Exp::Cast (_, _) =>
                                    bot_pred::<Exp>(),
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        Exp::New (_, _) =>
                            bot_pred::<Exp>(),
                        Exp::Cast (_, _) =>
                            bot_pred::<Exp>(),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        Exp::Var (_) =>
                            bot_pred::<Exp>(),
                        Exp::FieldProj (_, _) =>
                            bot_pred::<Exp>(),
                        Exp::MethodInvk (_, _, _) =>
                            bot_pred::<Exp>(),
                        Exp::New (_, _) =>
                            bot_pred::<Exp>(),
                        Exp::Cast (d, p1a) =>
                            match *p1a {
                                Exp::Var (_) =>
                                    bot_pred::<Exp>(),
                                Exp::FieldProj (_, _) =>
                                    bot_pred::<Exp>(),
                                Exp::MethodInvk (_, _, _) =>
                                    bot_pred::<Exp>(),
                                Exp::New (c, p2a) =>
                                    {
                                        let es = *p2a;
bind(
    subtyping_i_i_i(ct.clone(), c.clone(), d.clone()),
    (({
        let es_cap = es.clone();
        let c_cap = c.clone();
        Rc::new(move |Unit::Unity: Unit| -> Pred<Exp> {
            single(Exp::New (c_cap.clone(), Box::new(es_cap.clone())))
        })
    }) as Rc<dyn Fn(Unit) -> Pred<Exp>>)
)
                                    },
                                Exp::Cast (_, _) =>
                                    bot_pred::<Exp>(),
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (_, Exp::Var (_)) =>
                    bot_pred::<Exp>(),
                (ct, Exp::FieldProj (p0, f)) =>
                    {
                        let e0 = *p0;
                        bind(
                            reduce(ct.clone(), e0.clone()),
                            (({
                                let f_cap = f.clone();
                                Rc::new(move |xb: Exp| -> Pred<Exp> {
                                    single(Exp::FieldProj (Box::new(xb.clone()), f_cap.clone()))
                                })
                            }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
                        )
                    },
                (_, Exp::MethodInvk (_, _, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::New (_, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::Cast (_, _)) =>
                    bot_pred::<Exp>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (_, Exp::Var (_)) =>
                    bot_pred::<Exp>(),
                (_, Exp::FieldProj (_, _)) =>
                    bot_pred::<Exp>(),
                (ct, Exp::MethodInvk (p0, m, p1)) =>
                    {
                        let e0 = *p0;
                        let es = *p1;
                        bind(
                            reduce(ct.clone(), e0.clone()),
                            (({
                                let es_cap = es.clone();
                                let m_cap = m.clone();
                                Rc::new(move |xb: Exp| -> Pred<Exp> {
                                    single(Exp::MethodInvk (Box::new(xb.clone()), m_cap.clone(), Box::new(es_cap.clone())))
                                })
                            }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
                        )
                    },
                (_, Exp::New (_, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::Cast (_, _)) =>
                    bot_pred::<Exp>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (_, Exp::Var (_)) =>
                    bot_pred::<Exp>(),
                (_, Exp::FieldProj (_, _)) =>
                    bot_pred::<Exp>(),
                (ct, Exp::MethodInvk (p0, m, p1)) =>
                    {
                        let e = *p0;
                        let ea = *p1;
                        bind(
                            append_o_o_i(ea.clone()),
                            (({
                                let m_cap = m.clone();
                                let e_cap = e.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |aa: (List<Exp>, List<Exp>)| -> Pred<Exp> {
                                    match aa.clone() {
                                        (_, List::Nil) =>
    bot_pred::<Exp>(),
(el, List::Cons (ei, p0)) =>
    {
        let er = *p0;
        bind(
            reduce(ct_cap.clone(), ei.clone()),
            (({
                let m_capa = m_cap.clone();
                let e_capa = e_cap.clone();
                let er_cap = er.clone();
                let el_cap = el.clone();
                Rc::new(move |xb: Exp| -> Pred<Exp> {
                    bind(
                        append_i_i_o(el_cap.clone(), List::Cons (xb.clone(), Box::new(er_cap.clone()))),
                        (({
                            let m_capb = m_capa.clone();
                            let e_capb = e_capa.clone();
                            Rc::new(move |xc: List<Exp>| -> Pred<Exp> {
                                single(Exp::MethodInvk (Box::new(e_capb.clone()), m_capb.clone(), Box::new(xc.clone())))
                            })
                        }) as Rc<dyn Fn(List<Exp>) -> Pred<Exp>>)
                    )
                })
            }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
        )
    },
_ =>
    panic!("non-exhaustive match")
                                    }
                                })
                            }) as Rc<dyn Fn((List<Exp>, List<Exp>)) -> Pred<Exp>>)
                        )
                    },
                (_, Exp::New (_, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::Cast (_, _)) =>
                    bot_pred::<Exp>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (_, Exp::Var (_)) =>
                    bot_pred::<Exp>(),
                (_, Exp::FieldProj (_, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::MethodInvk (_, _, _)) =>
                    bot_pred::<Exp>(),
                (ct, Exp::New (c, p0)) =>
                    {
                        let ea = *p0;
                        bind(
                            append_o_o_i(ea.clone()),
                            (({
                                let c_cap = c.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |aa: (List<Exp>, List<Exp>)| -> Pred<Exp> {
                                    match aa.clone() {
                                        (_, List::Nil) =>
    bot_pred::<Exp>(),
(el, List::Cons (ei, p0)) =>
    {
        let er = *p0;
        bind(
            reduce(ct_cap.clone(), ei.clone()),
            (({
                let c_capa = c_cap.clone();
                let er_cap = er.clone();
                let el_cap = el.clone();
                Rc::new(move |xb: Exp| -> Pred<Exp> {
                    bind(
                        append_i_i_o(el_cap.clone(), List::Cons (xb.clone(), Box::new(er_cap.clone()))),
                        (({
                            let c_capb = c_capa.clone();
                            Rc::new(move |xc: List<Exp>| -> Pred<Exp> {
                                single(Exp::New (c_capb.clone(), Box::new(xc.clone())))
                            })
                        }) as Rc<dyn Fn(List<Exp>) -> Pred<Exp>>)
                    )
                })
            }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
        )
    },
_ =>
    panic!("non-exhaustive match")
                                    }
                                })
                            }) as Rc<dyn Fn((List<Exp>, List<Exp>)) -> Pred<Exp>>)
                        )
                    },
                (_, Exp::Cast (_, _)) =>
                    bot_pred::<Exp>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            match a.clone() {
                (_, Exp::Var (_)) =>
                    bot_pred::<Exp>(),
                (_, Exp::FieldProj (_, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::MethodInvk (_, _, _)) =>
                    bot_pred::<Exp>(),
                (_, Exp::New (_, _)) =>
                    bot_pred::<Exp>(),
                (ct, Exp::Cast (c, p0)) =>
                    {
                        let e0 = *p0;
                        bind(
                            reduce(ct.clone(), e0.clone()),
                            (({
                                let c_cap = c.clone();
                                Rc::new(move |xb: Exp| -> Pred<Exp> {
                                    single(Exp::Cast (c_cap.clone(), Box::new(xb.clone())))
                                })
                            }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ))))))))
}

pub fn classa__def () -> ClassDefExt<Unit> {
    ClassDefExt::ClassDefExt (suc(BigInt::ZERO), objecta(), List::Nil, ConstructorDefExt::ConstructorDefExt (suc(BigInt::ZERO), List::Nil, List::Nil, List::Nil, Unit::Unity), List::Nil, Unit::Unity)
}

pub fn classb__def () -> ClassDefExt<Unit> {
    ClassDefExt::ClassDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), List::Nil, ConstructorDefExt::ConstructorDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), List::Nil, List::Nil, List::Nil, Unit::Unity), List::Nil, Unit::Unity)
}

pub fn class_pair__def () -> ClassDefExt<Unit> {
    ClassDefExt::ClassDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), List::Cons (VarDefExt::VarDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[4]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), Unit::Unity), Box::new(List::Cons (VarDefExt::VarDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[5]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), Unit::Unity), Box::new(List::Nil)))), ConstructorDefExt::ConstructorDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), List::Cons (VarDefExt::VarDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[4]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), Unit::Unity), Box::new(List::Cons (VarDefExt::VarDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[5]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), Unit::Unity), Box::new(List::Nil)))), List::Nil, List::Cons ((match BigInt::from_bytes_be(Sign::Plus, &[4]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), Box::new(List::Cons ((match BigInt::from_bytes_be(Sign::Plus, &[5]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), Box::new(List::Nil)))), Unit::Unity), List::Cons (MethodDefExt::MethodDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), (match BigInt::from_bytes_be(Sign::Plus, &[6]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), List::Cons (VarDefExt::VarDefExt ((match BigInt::from_bytes_be(Sign::Plus, &[7]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), objecta(), Unit::Unity), Box::new(List::Nil)), Exp::New ((match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), Box::new(List::Cons (Exp::Var ((match BigInt::from_bytes_be(Sign::Plus, &[7]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), Box::new(List::Cons (Exp::FieldProj (Box::new(Exp::Var (this())), (match BigInt::from_bytes_be(Sign::Plus, &[5]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), Box::new(List::Nil)))))), Unit::Unity), Box::new(List::Nil)), Unit::Unity)
}

pub fn example_prog (x: BigInt) -> Option<ClassDefExt<Unit>> {
    (*fun_upd(((Rc::new(move |a: BigInt| -> Option<ClassDefExt<Unit>> {
        (*fun_upd(((Rc::new(move |aa: BigInt| -> Option<ClassDefExt<Unit>> {
            (*fun_upd(
                ((Rc::new(move |_: BigInt| -> Option<ClassDefExt<Unit>> {
                    Option::None
                })) as Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>),
                suc(BigInt::ZERO),
                Option::Some (classa__def())
            ))(aa.clone())
        })) as Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), Option::Some (classb__def())))(a.clone())
    })) as Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>), (match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), Option::Some (class_pair__def())))(x.clone())
}

pub fn append_i_o_i <A> (xa: List<A>, xb: List<A>) -> Pred<List<A>>
where
    A : Clone + Equal + 'static
{
    sup_pred(bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |a: (List<A>, List<A>)| -> Pred<List<A>> {
            match a.clone() {
                (List::Nil, xs) =>
                    single(xs.clone()),
                (List::Cons (_, _), _) =>
                    bot_pred::<List<A>>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ), bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |a: (List<A>, List<A>)| -> Pred<List<A>> {
            match a.clone() {
                (List::Nil, _) =>
                    bot_pred::<List<A>>(),
                (List::Cons (_, _), List::Nil) =>
                    bot_pred::<List<A>>(),
                (List::Cons (x, p0), List::Cons (xaa, p1)) =>
                    {
                        let xs = *p0;
                        let zs = *p1;
                        if eq(x.clone(), xaa.clone()) {
                            bind(append_i_o_i(xs.clone(), zs.clone()), ((Rc::new(move |aa: List<A>| -> Pred<List<A>> {
                                single(aa.clone())
                            })) as Rc<dyn Fn(List<A>) -> Pred<List<A>>>))
                        } else {
                            bot_pred::<List<A>>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ))
}

pub fn append_o_i_i <A> (xa: List<A>, xb: List<A>) -> Pred<List<A>>
where
    A : Clone + Equal + 'static
{
    sup_pred(bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |(xs, xsa): (List<A>, List<A>)| -> Pred<List<A>> {
            if <List<A> as Equal>::equal(xs.clone(), xsa.clone()) {
                single(List::Nil)
            } else {
                bot_pred::<List<A>>()
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ), bind(
        single((xa.clone(), xb.clone())),
        ((Rc::new(move |a: (List<A>, List<A>)| -> Pred<List<A>> {
            match a.clone() {
                (_, List::Nil) =>
                    bot_pred::<List<A>>(),
                (ys, List::Cons (x, p0)) =>
                    {
                        let zs = *p0;
                        bind(
                            append_o_i_i(ys.clone(), zs.clone()),
                            (({
                                let x_cap = x.clone();
                                Rc::new(move |xaa: List<A>| -> Pred<List<A>> {
                                    single(List::Cons (x_cap.clone(), Box::new(xaa.clone())))
                                })
                            }) as Rc<dyn Fn(List<A>) -> Pred<List<A>>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((List<A>, List<A>)) -> Pred<List<A>>>)
    ))
}

pub fn fields_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt,
      xb: List<VarDefExt<Unit>>) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, List<VarDefExt<Unit>>))| -> Pred<Unit> {
            match a.clone() {
                (_, (xc, List::Nil)) =>
                    if xc.clone() == objecta() {
                        single(Unit::Unity)
                    } else {
                        bot_pred::<Unit>()
                    },
                (_, (_, List::Cons (_, _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, List<VarDefExt<Unit>>))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (c, dgCf)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, List<VarDefExt<Unit>>))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let dgCf_cap = dgCf.clone();
                    let ct_cap = ct.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(c_super(cDef.clone())),
                                    (({
                                        let dgCf_capa = dgCf_cap.clone();
let cDef_cap = cDef.clone();
let ct_capa = ct_cap.clone();
Rc::new(move |xc: BigInt| -> Pred<Unit> {
    bind(
        fields_i_i_o(ct_capa.clone(), xc.clone()),
        (({
            let dgCf_capb = dgCf_capa.clone();
            let cDef_capa = cDef_cap.clone();
            Rc::new(move |xd: List<VarDefExt<Unit>>| -> Pred<Unit> {
                bind(
                    eq_i_o(c_fields(cDef_capa.clone())),
                    (({
                        let x_cap = xd.clone();
                        let dgCf_capc = dgCf_capb.clone();
                        Rc::new(move |xaa: List<VarDefExt<Unit>>| -> Pred<Unit> {
                            bind(
                                eq_i_i(dgCf_capc.clone(), crate::List::append(x_cap.clone(), xaa.clone())),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        })
                    }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, List<VarDefExt<Unit>>))) -> Pred<Unit>>)
    ))
}

pub fn subtypings_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: List<BigInt>,
      xb: List<BigInt>) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<BigInt>, List<BigInt>))| -> Pred<Unit> {
            match a.clone() {
                (_, (List::Nil, List::Nil)) =>
                    single(Unit::Unity),
                (_, (List::Nil, List::Cons (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (List::Cons (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<BigInt>, List<BigInt>))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<BigInt>, List<BigInt>))| -> Pred<Unit> {
            match a.clone() {
                (_, (List::Nil, _)) =>
                    bot_pred::<Unit>(),
                (_, (List::Cons (_, _), List::Nil)) =>
                    bot_pred::<Unit>(),
                (ct, (List::Cons (c0, p0), List::Cons (d0, p1))) =>
                    {
                        let cs = *p0;
                        let ds = *p1;
                        bind(
                            subtypings_i_i_i(ct.clone(), cs.clone(), ds.clone()),
                            (({
                                let d0_cap = d0.clone();
                                let c0_cap = c0.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    bind(
                                        subtyping_i_i_i(ct_cap.clone(), c0_cap.clone(), d0_cap.clone()),
((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    single(Unit::Unity)
})) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<BigInt>, List<BigInt>))) -> Pred<Unit>>)
    ))
}

pub fn subtypings_i_i_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xa: List<BigInt>) -> Pred<List<BigInt>> {
    sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, List<BigInt>)| -> Pred<List<BigInt>> {
            match a.clone() {
                (_, List::Nil) =>
                    single(List::Nil),
                (_, List::Cons (_, _)) =>
                    bot_pred::<List<BigInt>>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, List<BigInt>)) -> Pred<List<BigInt>>>)
    ), bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, List<BigInt>)| -> Pred<List<BigInt>> {
            match a.clone() {
                (_, List::Nil) =>
                    bot_pred::<List<BigInt>>(),
                (ct, List::Cons (c0, p0)) =>
                    {
                        let cs = *p0;
                        bind(
                            subtypings_i_i_o(ct.clone(), cs.clone()),
                            (({
                                let c0_cap = c0.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |xb: List<BigInt>| -> Pred<List<BigInt>> {
                                    bind(
                                        supertypes_of(ct_cap.clone(), c0_cap.clone()),
(({
    let x_cap = xb.clone();
    Rc::new(move |xaa: BigInt| -> Pred<List<BigInt>> {
        single(List::Cons (xaa.clone(), Box::new(x_cap.clone())))
    })
}) as Rc<dyn Fn(BigInt) -> Pred<List<BigInt>>>)
                                    )
                                })
                            }) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, List<BigInt>)) -> Pred<List<BigInt>>>)
    ))
}

pub fn mtype_i_i_i_i_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: List<BigInt>) -> Pred<BigInt> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, bs))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))| -> Pred<BigInt> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let bs_cap = bs.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<BigInt> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<BigInt>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let bs_capa = bs_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<BigInt> {
    match aa.clone() {
        Option::None =>
            bot_pred::<BigInt>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(var_defs_types(m_params(mDef.clone())), bs_capa.clone()),
                (({
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
                        bind(eq_i_o(m_return(mDef_cap.clone())), ((Rc::new(move |ab: BigInt| -> Pred<BigInt> {
                            single(ab.clone())
                        })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>))
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<BigInt>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<BigInt>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))) -> Pred<BigInt>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, bs))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))| -> Pred<BigInt> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let bs_cap = bs.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<BigInt> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<BigInt>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let bs_capa = bs_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let bs_capb = bs_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xd: BigInt| -> Pred<BigInt> {
                bind(mtype_i_i_i_i_o(ct_capb.clone(), m_capb.clone(), xd.clone(), bs_capb.clone()), ((Rc::new(move |aa: BigInt| -> Pred<BigInt> {
                    single(aa.clone())
                })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>))
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<BigInt>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))) -> Pred<BigInt>>)
    ))
}

pub fn typings_i_i_i_o
    (xa: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xb: Rc<dyn Fn(BigInt) -> Option<BigInt>>,
      xc: List<Exp>) -> Pred<List<BigInt>> {
    sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, List<Exp>))| -> Pred<List<BigInt>> {
            match a.clone() {
                (_, (_, List::Nil)) =>
                    single(List::Nil),
                (_, (_, List::Cons (_, _))) =>
                    bot_pred::<List<BigInt>>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, List<Exp>))) -> Pred<List<BigInt>>>)
    ), bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, List<Exp>))| -> Pred<List<BigInt>> {
            match a.clone() {
                (_, (_, List::Nil)) =>
                    bot_pred::<List<BigInt>>(),
                (ct, (gamma, List::Cons (e0, p0))) =>
                    {
                        let es = *p0;
                        bind(
                            typings_i_i_i_o(ct.clone(), gamma.clone(), es.clone()),
                            (({
                                let e0_cap = e0.clone();
                                let gamma_cap = gamma.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: List<BigInt>| -> Pred<List<BigInt>> {
                                    bind(
                                        typing_i_i_i_o(ct_cap.clone(), gamma_cap.clone(), e0_cap.clone()),
(({
    let x_cap = x.clone();
    Rc::new(move |xaa: BigInt| -> Pred<List<BigInt>> {
        single(List::Cons (xaa.clone(), Box::new(x_cap.clone())))
    })
}) as Rc<dyn Fn(BigInt) -> Pred<List<BigInt>>>)
                                    )
                                })
                            }) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, List<Exp>))) -> Pred<List<BigInt>>>)
    ))
}

pub fn typing_i_i_i_o
    (xa: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xb: Rc<dyn Fn(BigInt) -> Option<BigInt>>, xc: Exp) -> Pred<BigInt> {
    sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (gamma, Exp::Var (x))) =>
                    bind(
                        eq_i_o((*gamma)(x.clone())),
                        ((Rc::new(move |aa: Option<BigInt>| -> Pred<BigInt> {
                            match aa.clone() {
                                Option::None =>
                                    bot_pred::<BigInt>(),
                                Option::Some (ab) =>
                                    single(ab.clone()),
                                _ =>
                                    panic!("non-exhaustive match")
                            }
                        })) as Rc<dyn Fn(Option<BigInt>) -> Pred<BigInt>>)
                    ),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::Cast (_, _))) =>
                    bot_pred::<BigInt>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::FieldProj (p0, fi))) =>
                    {
                        let e0 = *p0;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let fi_cap = fi.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<BigInt> {
                                    bind(
                                        fields_i_i_o(ct_cap.clone(), x.clone()),
(({
    let fi_capa = fi_cap.clone();
    Rc::new(move |xd: List<VarDefExt<Unit>>| -> Pred<BigInt> {
        bind(
            eq_i_o(lookup(
                xd.clone(),
                (({
                    let fi_capb = fi_capa.clone();
                    Rc::new(move |fd: VarDefExt<Unit>| -> bool {
                        vd_name(fd.clone()) == fi_capb.clone()
                    })
                }) as Rc<dyn Fn(VarDefExt<Unit>) -> bool>)
            )),
            ((Rc::new(move |aa: Option<VarDefExt<Unit>>| -> Pred<BigInt> {
                match aa.clone() {
                    Option::None =>
                        bot_pred::<BigInt>(),
                    Option::Some (fDef) =>
                        bind(eq_i_o(vd_type(fDef.clone())), ((Rc::new(move |ab: BigInt| -> Pred<BigInt> {
                            single(ab.clone())
                        })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)),
                    _ =>
                        panic!("non-exhaustive match")
                }
            })) as Rc<dyn Fn(Option<VarDefExt<Unit>>) -> Pred<BigInt>>)
        )
    })
}) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
                        )
                    },
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::Cast (_, _))) =>
                    bot_pred::<BigInt>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::MethodInvk (p0, m, p1))) =>
                    {
                        let e0 = *p0;
                        let es = *p1;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let m_cap = m.clone();
                                let es_cap = es.clone();
                                let gamma_cap = gamma.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<BigInt> {
                                    bind(
                                        typings_i_i_i_o(ct_cap.clone(), gamma_cap.clone(), es_cap.clone()),
(({
    let x_cap = x.clone();
    let m_capa = m_cap.clone();
    let es_capa = es_cap.clone();
    let ct_capa = ct_cap.clone();
    Rc::new(move |xaa: List<BigInt>| -> Pred<BigInt> {
        bind(
            subtypings_i_i_o(ct_capa.clone(), xaa.clone()),
            (({
                let x_capa = x_cap.clone();
                let m_capb = m_capa.clone();
                let ct_capb = ct_capa.clone();
                let es_capb = es_capa.clone();
                Rc::new(move |xab: List<BigInt>| -> Pred<BigInt> {
                    bind(
                        eq_i_i(size_lista(es_capb.clone()), size_lista(xab.clone())),
                        (({
                            let xa_cap = xab.clone();
                            let x_capb = x_capa.clone();
                            let m_capc = m_capb.clone();
                            let ct_capc = ct_capb.clone();
                            Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
                                bind(mtype_i_i_i_i_o(ct_capc.clone(), m_capc.clone(), x_capb.clone(), xa_cap.clone()), ((Rc::new(move |aa: BigInt| -> Pred<BigInt> {
                                    single(aa.clone())
                                })) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>))
                            })
                        }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                    )
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Pred<BigInt>>)
        )
    })
}) as Rc<dyn Fn(List<BigInt>) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
                        )
                    },
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::Cast (_, _))) =>
                    bot_pred::<BigInt>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::New (c, p0))) =>
                    {
                        let es = *p0;
                        bind(
                            fields_i_i_o(ct.clone(), c.clone()),
                            (({
                                let c_cap = c.clone();
                                let gamma_cap = gamma.clone();
                                let ct_cap = ct.clone();
                                let es_cap = es.clone();
                                Rc::new(move |x: List<VarDefExt<Unit>>| -> Pred<BigInt> {
                                    bind(
                                        eq_i_i(size_lista(es_cap.clone()), size_lista(x.clone())),
(({
    let c_capa = c_cap.clone();
    let es_capa = es_cap.clone();
    let gamma_capa = gamma_cap.clone();
    let ct_capa = ct_cap.clone();
    let x_cap = x.clone();
    Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
        bind(
            eq_i_o(var_defs_types(x_cap.clone())),
            (({
                let c_capb = c_capa.clone();
                let es_capb = es_capa.clone();
                let gamma_capb = gamma_capa.clone();
                let ct_capb = ct_capa.clone();
                Rc::new(move |xd: List<BigInt>| -> Pred<BigInt> {
                    bind(
                        typings_i_i_i_o(ct_capb.clone(), gamma_capb.clone(), es_capb.clone()),
                        (({
                            let c_capc = c_capb.clone();
                            let x_capa = xd.clone();
                            let ct_capc = ct_capb.clone();
                            Rc::new(move |xaa: List<BigInt>| -> Pred<BigInt> {
                                bind(
                                    subtypings_i_i_i(ct_capc.clone(), xaa.clone(), x_capa.clone()),
                                    (({
                                        let c_capd = c_capc.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
    single(c_capd.clone())
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                )
                            })
                        }) as Rc<dyn Fn(List<BigInt>) -> Pred<BigInt>>)
                    )
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Pred<BigInt>>)
        )
    })
}) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<BigInt>>)
                        )
                    },
                (_, (_, Exp::Cast (_, _))) =>
                    bot_pred::<BigInt>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::Cast (c, p0))) =>
                    {
                        let e0 = *p0;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let c_cap = c.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<BigInt> {
                                    bind(
                                        subtyping_i_i_i(ct_cap.clone(), x.clone(), c_cap.clone()),
(({
    let c_capa = c_cap.clone();
    Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
        single(c_capa.clone())
    })
}) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::Cast (c, p0))) =>
                    {
                        let e0 = *p0;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let c_cap = c.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<BigInt> {
                                    bind(
                                        subtyping_i_i_i(ct_cap.clone(), c_cap.clone(), x.clone()),
(({
    let x_cap = x.clone();
    let c_capa = c_cap.clone();
    Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
        bind(
            if_pred(! (c_capa.clone() == x_cap.clone())),
            (({
                let c_capb = c_capa.clone();
                Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
                    single(c_capb.clone())
                })
            }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
        )
    })
}) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    ), bind(
        single((xa.clone(), (xb.clone(), xc.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))| -> Pred<BigInt> {
            match a.clone() {
                (_, (_, Exp::Var (_))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::FieldProj (_, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<BigInt>(),
                (_, (_, Exp::New (_, _))) =>
                    bot_pred::<BigInt>(),
                (ct, (gamma, Exp::Cast (c, p0))) =>
                    {
                        let e0 = *p0;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let c_cap = c.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<BigInt> {
                                    bind(
                                        not_pred(subtyping_i_i_i(ct_cap.clone(), c_cap.clone(), x.clone())),
(({
    let c_capa = c_cap.clone();
    let x_cap = x.clone();
    let ct_capa = ct_cap.clone();
    Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
        bind(
            not_pred(subtyping_i_i_i(ct_capa.clone(), x_cap.clone(), c_capa.clone())),
            (({
                let c_capb = c_capa.clone();
                Rc::new(move |Unit::Unity: Unit| -> Pred<BigInt> {
                    single(c_capb.clone())
                })
            }) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
        )
    })
}) as Rc<dyn Fn(Unit) -> Pred<BigInt>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<BigInt>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, Exp))) -> Pred<BigInt>>)
    )))))))
}

pub fn mtype_i_i_i_o_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: BigInt) -> Pred<List<BigInt>> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, b))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, BigInt)))| -> Pred<List<BigInt>> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let b_cap = b.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<List<BigInt>> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<List<BigInt>>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let b_capa = b_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<List<BigInt>> {
    match aa.clone() {
        Option::None =>
            bot_pred::<List<BigInt>>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(m_return(mDef.clone()), b_capa.clone()),
                (({
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<List<BigInt>> {
                        bind(eq_i_o(var_defs_types(m_params(mDef_cap.clone()))), ((Rc::new(move |ab: List<BigInt>| -> Pred<List<BigInt>> {
                            single(ab.clone())
                        })) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>))
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<List<BigInt>>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<List<BigInt>>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<List<BigInt>>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, BigInt)))) -> Pred<List<BigInt>>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, b))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, BigInt)))| -> Pred<List<BigInt>> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let b_cap = b.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<List<BigInt>> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<List<BigInt>>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let b_capa = b_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<List<BigInt>> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let b_capb = b_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xd: BigInt| -> Pred<List<BigInt>> {
                bind(mtype_i_i_i_o_i(ct_capb.clone(), m_capb.clone(), xd.clone(), b_capb.clone()), ((Rc::new(move |aa: List<BigInt>| -> Pred<List<BigInt>> {
                    single(aa.clone())
                })) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>))
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<List<BigInt>>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<List<BigInt>>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<List<BigInt>>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, BigInt)))) -> Pred<List<BigInt>>>)
    ))
}

pub fn typing_i_i_i_i
    (xa: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xb: Rc<dyn Fn(BigInt) -> Option<BigInt>>, xc: Exp,
      xd: BigInt) -> Pred<Unit> {
    sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (gamma, (Exp::Var (x), c))) =>
                    bind(
                        eq_i_i((*gamma)(x.clone()), Option::Some (c.clone())),
                        ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                            single(Unit::Unity)
                        })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                    ),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::Cast (_, _), _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::FieldProj (p0, fi), ci))) =>
                    {
                        let e0 = *p0;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let ci_cap = ci.clone();
                                let fi_cap = fi.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<Unit> {
                                    bind(
                                        fields_i_i_o(ct_cap.clone(), x.clone()),
(({
    let ci_capa = ci_cap.clone();
    let fi_capa = fi_cap.clone();
    Rc::new(move |xe: List<VarDefExt<Unit>>| -> Pred<Unit> {
        bind(
            eq_i_o(lookup(
                xe.clone(),
                (({
                    let fi_capb = fi_capa.clone();
                    Rc::new(move |fd: VarDefExt<Unit>| -> bool {
                        vd_name(fd.clone()) == fi_capb.clone()
                    })
                }) as Rc<dyn Fn(VarDefExt<Unit>) -> bool>)
            )),
            (({
                let ci_capb = ci_capa.clone();
                Rc::new(move |aa: Option<VarDefExt<Unit>>| -> Pred<Unit> {
                    match aa.clone() {
                        Option::None =>
                            bot_pred::<Unit>(),
                        Option::Some (fDef) =>
                            bind(
                                eq_i_i(vd_type(fDef.clone()), ci_capb.clone()),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            ),
                        _ =>
                            panic!("non-exhaustive match")
                    }
                })
            }) as Rc<dyn Fn(Option<VarDefExt<Unit>>) -> Pred<Unit>>)
        )
    })
}) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                        )
                    },
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::Cast (_, _), _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::MethodInvk (p0, m, p1), c))) =>
                    {
                        let e0 = *p0;
                        let es = *p1;
                        bind(
                            typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                            (({
                                let gamma_cap = gamma.clone();
                                let es_cap = es.clone();
                                let c_cap = c.clone();
                                let m_cap = m.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |x: BigInt| -> Pred<Unit> {
                                    bind(
                                        mtype_i_i_i_o_i(ct_cap.clone(), m_cap.clone(), x.clone(), c_cap.clone()),
(({
    let gamma_capa = gamma_cap.clone();
    let ct_capa = ct_cap.clone();
    let es_capa = es_cap.clone();
    Rc::new(move |xe: List<BigInt>| -> Pred<Unit> {
        bind(
            eq_i_i(size_lista(es_capa.clone()), size_lista(xe.clone())),
            (({
                let x_cap = xe.clone();
                let es_capb = es_capa.clone();
                let gamma_capb = gamma_capa.clone();
                let ct_capb = ct_capa.clone();
                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                    bind(
                        typings_i_i_i_o(ct_capb.clone(), gamma_capb.clone(), es_capb.clone()),
                        (({
                            let x_capa = x_cap.clone();
                            let ct_capc = ct_capb.clone();
                            Rc::new(move |xaa: List<BigInt>| -> Pred<Unit> {
                                bind(
                                    subtypings_i_i_i(ct_capc.clone(), xaa.clone(), x_capa.clone()),
                                    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                        single(Unit::Unity)
                                    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                )
                            })
                        }) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
                    )
                })
            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
        )
    })
}) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                        )
                    },
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::Cast (_, _), _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::New (c, p0), ca))) =>
                    {
                        let es = *p0;
                        if c.clone() == ca.clone() {
                            bind(
                                fields_i_i_o(ct.clone(), c.clone()),
                                (({
                                    let gamma_cap = gamma.clone();
                                    let ct_cap = ct.clone();
                                    let es_cap = es.clone();
                                    Rc::new(move |x: List<VarDefExt<Unit>>| -> Pred<Unit> {
                                        bind(
    eq_i_i(size_lista(es_cap.clone()), size_lista(x.clone())),
    (({
        let es_capa = es_cap.clone();
        let gamma_capa = gamma_cap.clone();
        let ct_capa = ct_cap.clone();
        let x_cap = x.clone();
        Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
            bind(
                eq_i_o(var_defs_types(x_cap.clone())),
                (({
                    let es_capb = es_capa.clone();
                    let gamma_capb = gamma_capa.clone();
                    let ct_capb = ct_capa.clone();
                    Rc::new(move |xe: List<BigInt>| -> Pred<Unit> {
                        bind(
                            typings_i_i_i_o(ct_capb.clone(), gamma_capb.clone(), es_capb.clone()),
                            (({
                                let x_capa = xe.clone();
                                let ct_capc = ct_capb.clone();
                                Rc::new(move |xaa: List<BigInt>| -> Pred<Unit> {
                                    bind(
                                        subtypings_i_i_i(ct_capc.clone(), xaa.clone(), x_capa.clone()),
((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    single(Unit::Unity)
})) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
            )
        })
    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                (_, (_, (Exp::Cast (_, _), _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::Cast (c, p0), ca))) =>
                    {
                        let e0 = *p0;
                        if c.clone() == ca.clone() {
                            bind(
                                typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                                (({
                                    let c_cap = c.clone();
                                    let ct_cap = ct.clone();
                                    Rc::new(move |x: BigInt| -> Pred<Unit> {
                                        bind(
    subtyping_i_i_i(ct_cap.clone(), x.clone(), c_cap.clone()),
    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
        single(Unit::Unity)
    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::Cast (c, p0), ca))) =>
                    {
                        let e0 = *p0;
                        if c.clone() == ca.clone() {
                            bind(
                                typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                                (({
                                    let c_cap = c.clone();
                                    let ct_cap = ct.clone();
                                    Rc::new(move |x: BigInt| -> Pred<Unit> {
                                        bind(
    subtyping_i_i_i(ct_cap.clone(), c_cap.clone(), x.clone()),
    (({
        let x_cap = x.clone();
        let c_capa = c_cap.clone();
        Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
            bind(
                if_pred(! (c_capa.clone() == x_cap.clone())),
                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                    single(Unit::Unity)
                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
            )
        })
    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    ), bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (Exp::Var (_), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::FieldProj (_, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::MethodInvk (_, _, _), _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (Exp::New (_, _), _))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (Exp::Cast (c, p0), ca))) =>
                    {
                        let e0 = *p0;
                        if c.clone() == ca.clone() {
                            bind(
                                typing_i_i_i_o(ct.clone(), gamma.clone(), e0.clone()),
                                (({
                                    let c_cap = c.clone();
                                    let ct_cap = ct.clone();
                                    Rc::new(move |x: BigInt| -> Pred<Unit> {
                                        bind(
    not_pred(subtyping_i_i_i(ct_cap.clone(), c_cap.clone(), x.clone())),
    (({
        let c_capa = c_cap.clone();
        let x_cap = x.clone();
        let ct_capa = ct_cap.clone();
        Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
            bind(
                not_pred(subtyping_i_i_i(ct_capa.clone(), x_cap.clone(), c_capa.clone())),
                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                    single(Unit::Unity)
                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
            )
        })
    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (Exp, BigInt)))) -> Pred<Unit>>)
    )))))))
}

pub fn mbody_i_i_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: List<BigInt>, xd: Exp) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (c, (xs, e)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, Exp))))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let e_cap = e.clone();
                    let xs_cap = xs.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let e_capa = e_cap.clone();
let xs_capa = xs_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<Unit> {
    match aa.clone() {
        Option::None =>
            bot_pred::<Unit>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(var_defs_names(m_params(mDef.clone())), xs_capa.clone()),
                (({
                    let e_capb = e_capa.clone();
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                        bind(
                            eq_i_i(m_body(mDef_cap.clone()), e_capb.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, Exp))))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (c, (xs, e)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, Exp))))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let e_cap = e.clone();
                    let xs_cap = xs.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let e_capa = e_cap.clone();
let xs_capa = xs_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let e_capb = e_capa.clone();
            let xs_capb = xs_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xe: BigInt| -> Pred<Unit> {
                bind(
                    mbody_i_i_i_i_i(ct_capb.clone(), m_capb.clone(), xe.clone(), xs_capb.clone(), e_capb.clone()),
                    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                        single(Unit::Unity)
                    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, Exp))))) -> Pred<Unit>>)
    ))
}

pub fn mbody_i_i_i_i_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: List<BigInt>) -> Pred<Exp> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, xs))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))| -> Pred<Exp> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let xs_cap = xs.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Exp> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Exp>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let xs_capa = xs_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<Exp> {
    match aa.clone() {
        Option::None =>
            bot_pred::<Exp>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(var_defs_names(m_params(mDef.clone())), xs_capa.clone()),
                (({
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<Exp> {
                        bind(eq_i_o(m_body(mDef_cap.clone())), ((Rc::new(move |ab: Exp| -> Pred<Exp> {
                            single(ab.clone())
                        })) as Rc<dyn Fn(Exp) -> Pred<Exp>>))
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<Exp>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<Exp>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Exp>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))) -> Pred<Exp>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, xs))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))| -> Pred<Exp> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let xs_cap = xs.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Exp> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Exp>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let xs_capa = xs_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<Exp> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let xs_capb = xs_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xd: BigInt| -> Pred<Exp> {
                bind(mbody_i_i_i_i_o(ct_capb.clone(), m_capb.clone(), xd.clone(), xs_capb.clone()), ((Rc::new(move |aa: Exp| -> Pred<Exp> {
                    single(aa.clone())
                })) as Rc<dyn Fn(Exp) -> Pred<Exp>>))
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<Exp>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<Exp>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Exp>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, List<BigInt>)))) -> Pred<Exp>>)
    ))
}

pub fn mbody_i_i_i_o_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: Exp) -> Pred<List<BigInt>> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, e))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, Exp)))| -> Pred<List<BigInt>> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let e_cap = e.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<List<BigInt>> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<List<BigInt>>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let e_capa = e_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<List<BigInt>> {
    match aa.clone() {
        Option::None =>
            bot_pred::<List<BigInt>>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(m_body(mDef.clone()), e_capa.clone()),
                (({
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<List<BigInt>> {
                        bind(eq_i_o(var_defs_names(m_params(mDef_cap.clone()))), ((Rc::new(move |ab: List<BigInt>| -> Pred<List<BigInt>> {
                            single(ab.clone())
                        })) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>))
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<List<BigInt>>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<List<BigInt>>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<List<BigInt>>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, Exp)))) -> Pred<List<BigInt>>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), xc.clone())))),
        ((Rc::new(move |(ct, (m, (c, e))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, Exp)))| -> Pred<List<BigInt>> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let e_cap = e.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<List<BigInt>> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<List<BigInt>>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let e_capa = e_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<List<BigInt>> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let e_capb = e_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xd: BigInt| -> Pred<List<BigInt>> {
                bind(mbody_i_i_i_o_i(ct_capb.clone(), m_capb.clone(), xd.clone(), e_capb.clone()), ((Rc::new(move |aa: List<BigInt>| -> Pred<List<BigInt>> {
                    single(aa.clone())
                })) as Rc<dyn Fn(List<BigInt>) -> Pred<List<BigInt>>>))
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<List<BigInt>>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<List<BigInt>>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<List<BigInt>>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, Exp)))) -> Pred<List<BigInt>>>)
    ))
}

pub fn mtype_i_i_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: List<BigInt>, xd: BigInt) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (c, (bs, b)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let b_cap = b.clone();
                    let bs_cap = bs.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    (({
                                        let b_capa = b_cap.clone();
let bs_capa = bs_cap.clone();
Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<Unit> {
    match aa.clone() {
        Option::None =>
            bot_pred::<Unit>(),
        Option::Some (mDef) =>
            bind(
                eq_i_i(var_defs_types(m_params(mDef.clone())), bs_capa.clone()),
                (({
                    let b_capb = b_capa.clone();
                    let mDef_cap = mDef.clone();
                    Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                        bind(
                            eq_i_i(m_return(mDef_cap.clone()), b_capb.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
})
                                    }) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (c, (bs, b)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let b_cap = b.clone();
                    let bs_cap = bs.clone();
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let b_capa = b_cap.clone();
let bs_capa = bs_cap.clone();
let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let b_capb = b_capa.clone();
            let bs_capb = bs_capa.clone();
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xe: BigInt| -> Pred<Unit> {
                bind(
                    mtype_i_i_i_i_i(ct_capb.clone(), m_capb.clone(), xe.clone(), bs_capb.clone(), b_capb.clone()),
                    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                        single(Unit::Unity)
                    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))) -> Pred<Unit>>)
    ))
}

pub fn mtype_i_i_i_o_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt,
      xb: BigInt) -> Pred<(List<BigInt>, BigInt)> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (m, c)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<(List<BigInt>, BigInt)> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<(List<BigInt>, BigInt)> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<(List<BigInt>, BigInt)>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_o(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    )),
                                    ((Rc::new(move |aa: Option<MethodDefExt<Unit>>| -> Pred<(List<BigInt>, BigInt)> {
                                        match aa.clone() {
    Option::None =>
        bot_pred::<(List<BigInt>, BigInt)>(),
    Option::Some (mDef) =>
        bind(
            eq_i_o(var_defs_types(m_params(mDef.clone()))),
            (({
                let mDef_cap = mDef.clone();
                Rc::new(move |xc: List<BigInt>| -> Pred<(List<BigInt>, BigInt)> {
                    bind(
                        eq_i_o(m_return(mDef_cap.clone())),
                        (({
                            let x_cap = xc.clone();
                            Rc::new(move |xaa: BigInt| -> Pred<(List<BigInt>, BigInt)> {
                                single((x_cap.clone(), xaa.clone()))
                            })
                        }) as Rc<dyn Fn(BigInt) -> Pred<(List<BigInt>, BigInt)>>)
                    )
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Pred<(List<BigInt>, BigInt)>>)
        ),
    _ =>
        panic!("non-exhaustive match")
}
                                    })) as Rc<dyn Fn(Option<MethodDefExt<Unit>>) -> Pred<(List<BigInt>, BigInt)>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<(List<BigInt>, BigInt)>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<(List<BigInt>, BigInt)>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (m, c)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))| -> Pred<(List<BigInt>, BigInt)> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let ct_cap = ct.clone();
                    let m_cap = m.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<(List<BigInt>, BigInt)> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<(List<BigInt>, BigInt)>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(lookup(
                                        c_methods(cDef.clone()),
(({
    let m_capa = m_cap.clone();
    Rc::new(move |md: MethodDefExt<Unit>| -> bool {
        m_name(md.clone()) == m_capa.clone()
    })
}) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                    ), Option::None),
                                    (({
                                        let m_capa = m_cap.clone();
let ct_capa = ct_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<(List<BigInt>, BigInt)> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let m_capb = m_capa.clone();
            let ct_capb = ct_capa.clone();
            Rc::new(move |xc: BigInt| -> Pred<(List<BigInt>, BigInt)> {
                bind(
                    mtype_i_i_i_o_o(ct_capb.clone(), m_capb.clone(), xc.clone()),
                    ((Rc::new(move |(bs, b): (List<BigInt>, BigInt)| -> Pred<(List<BigInt>, BigInt)> {
                        single((bs.clone(), b.clone()))
                    })) as Rc<dyn Fn((List<BigInt>, BigInt)) -> Pred<(List<BigInt>, BigInt)>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<(List<BigInt>, BigInt)>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<(List<BigInt>, BigInt)>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<(List<BigInt>, BigInt)>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, BigInt))) -> Pred<(List<BigInt>, BigInt)>>)
    ))
}

pub fn reduction_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: Exp,
      xb: Exp) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        (p1, ei) =>
                            match p1 {
                                Exp::Var (_) =>
                                    bot_pred::<Unit>(),
                                Exp::FieldProj (p2, fi) =>
                                    match *p2 {
                                        Exp::Var (_) =>
    bot_pred::<Unit>(),
Exp::FieldProj (_, _) =>
    bot_pred::<Unit>(),
Exp::MethodInvk (_, _, _) =>
    bot_pred::<Unit>(),
Exp::New (c, p3a) =>
    {
        let es = *p3a;
        bind(
            fields_i_i_o(ct.clone(), c.clone()),
            (({
                let ei_cap = ei.clone();
                let fi_cap = fi.clone();
                let es_cap = es.clone();
                Rc::new(move |xc: List<VarDefExt<Unit>>| -> Pred<Unit> {
                    bind(
                        eq_i_i(lookup2(
                            xc.clone(),
                            es_cap.clone(),
                            (({
                                let fi_capa = fi_cap.clone();
                                Rc::new(move |fd: VarDefExt<Unit>| -> bool {
                                    vd_name(fd.clone()) == fi_capa.clone()
                                })
                            }) as Rc<dyn Fn(VarDefExt<Unit>) -> bool>)
                        ), Option::Some (ei_cap.clone())),
                        ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                            single(Unit::Unity)
                        })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                    )
                })
            }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
        )
    },
Exp::Cast (_, _) =>
    bot_pred::<Unit>(),
_ =>
    panic!("non-exhaustive match")
                                    },
                                Exp::MethodInvk (_, _, _) =>
                                    bot_pred::<Unit>(),
                                Exp::New (_, _) =>
                                    bot_pred::<Unit>(),
                                Exp::Cast (_, _) =>
                                    bot_pred::<Unit>(),
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        (p1, e0) =>
                            match p1 {
                                Exp::Var (_) =>
                                    bot_pred::<Unit>(),
                                Exp::FieldProj (_, _) =>
                                    bot_pred::<Unit>(),
                                Exp::MethodInvk (p2, m, p2b) =>
                                    match *p2 {
                                        Exp::Var (_) =>
    bot_pred::<Unit>(),
Exp::FieldProj (_, _) =>
    bot_pred::<Unit>(),
Exp::MethodInvk (_, _, _) =>
    bot_pred::<Unit>(),
Exp::New (c, p3a) =>
    {
        let es = *p3a;
        let ds = *p2b;
        bind(
            mbody_i_i_i_o_o(ct.clone(), m.clone(), c.clone()),
            (({
                let e0_cap = e0.clone();
                let es_cap = es.clone();
                let c_cap = c.clone();
                let ds_cap = ds.clone();
                Rc::new(move |(xs, e0a): (List<BigInt>, Exp)| -> Pred<Unit> {
                    bind(
                        eq_i_i(substs((({
                            let es_capa = es_cap.clone();
                            let c_capa = c_cap.clone();
                            let ds_capa = ds_cap.clone();
                            let xs_cap = xs.clone();
                            Rc::new(move |aa: BigInt| -> Option<Exp> {
                                (*fun_upd((({
                                    let ds_capb = ds_capa.clone();
                                    let xs_capa = xs_cap.clone();
                                    Rc::new(move |ab: BigInt| -> Option<Exp> {
                                        (*map_upds(
    ((Rc::new(move |_: BigInt| -> Option<Exp> {
        Option::None
    })) as Rc<dyn Fn(BigInt) -> Option<Exp>>),
    xs_capa.clone(),
    ds_capb.clone()
))(ab.clone())
                                    })
                                }) as Rc<dyn Fn(BigInt) -> Option<Exp>>), this(), Option::Some (Exp::New (c_capa.clone(), Box::new(es_capa.clone())))))(aa.clone())
                            })
                        }) as Rc<dyn Fn(BigInt) -> Option<Exp>>), e0a.clone()), e0_cap.clone()),
                        ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                            single(Unit::Unity)
                        })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                    )
                })
            }) as Rc<dyn Fn((List<BigInt>, Exp)) -> Pred<Unit>>)
        )
    },
Exp::Cast (_, _) =>
    bot_pred::<Unit>(),
_ =>
    panic!("non-exhaustive match")
                                    },
                                Exp::New (_, _) =>
                                    bot_pred::<Unit>(),
                                Exp::Cast (_, _) =>
                                    bot_pred::<Unit>(),
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (ct, p0a) =>
                    match p0a {
                        (p1, p1a) =>
                            match p1 {
                                Exp::Var (_) =>
                                    bot_pred::<Unit>(),
                                Exp::FieldProj (_, _) =>
                                    bot_pred::<Unit>(),
                                Exp::MethodInvk (_, _, _) =>
                                    bot_pred::<Unit>(),
                                Exp::New (_, _) =>
                                    bot_pred::<Unit>(),
                                Exp::Cast (d, p2a) =>
                                    match *p2a {
                                        Exp::Var (_) =>
    bot_pred::<Unit>(),
Exp::FieldProj (_, _) =>
    bot_pred::<Unit>(),
Exp::MethodInvk (_, _, _) =>
    bot_pred::<Unit>(),
Exp::New (c, p3a) =>
    match p1a {
        Exp::Var (_) =>
            bot_pred::<Unit>(),
        Exp::FieldProj (_, _) =>
            bot_pred::<Unit>(),
        Exp::MethodInvk (_, _, _) =>
            bot_pred::<Unit>(),
        Exp::New (ca, p4a) =>
            {
                let es = *p3a;
                let esa = *p4a;
                if <List<Exp> as Equal>::equal(es.clone(), esa.clone()) &&
                     c.clone() == ca.clone() {
                    bind(
                        subtyping_i_i_i(ct.clone(), c.clone(), d.clone()),
                        ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                            single(Unit::Unity)
                        })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                    )
                } else {
                    bot_pred::<Unit>()
                }
            },
        Exp::Cast (_, _) =>
            bot_pred::<Unit>(),
        _ =>
            panic!("non-exhaustive match")
    },
Exp::Cast (_, _) =>
    bot_pred::<Unit>(),
_ =>
    panic!("non-exhaustive match")
                                    },
                                _ =>
                                    panic!("non-exhaustive match")
                            },
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (_, (Exp::Var (_), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), Exp::Var (_))) =>
                    bot_pred::<Unit>(),
                (ct, (Exp::FieldProj (p0, f), Exp::FieldProj (p1, fa))) =>
                    {
                        let e0 = *p0;
                        let e0a = *p1;
                        if f.clone() == fa.clone() {
                            bind(
                                reduction_i_i_i(ct.clone(), e0.clone(), e0a.clone()),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                (_, (Exp::FieldProj (_, _), Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), Exp::New (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), Exp::Cast (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (_, (Exp::Var (_), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::Var (_))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::FieldProj (_, _))) =>
                    bot_pred::<Unit>(),
                (ct, (Exp::MethodInvk (p0, m, p1), Exp::MethodInvk (p2, ma, p3))) =>
                    {
                        let e0 = *p0;
                        let es = *p1;
                        let e0a = *p2;
                        let esa = *p3;
                        if <List<Exp> as Equal>::equal(es.clone(), esa.clone()) &&
                             m.clone() == ma.clone() {
                            bind(
                                reduction_i_i_i(ct.clone(), e0.clone(), e0a.clone()),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                (_, (Exp::MethodInvk (_, _, _), Exp::New (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::Cast (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (_, (Exp::Var (_), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::Var (_))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::FieldProj (_, _))) =>
                    bot_pred::<Unit>(),
                (ct, (Exp::MethodInvk (p0, m, p1), Exp::MethodInvk (p2, ma, p3))) =>
                    {
                        let e = *p0;
                        let ea = *p1;
                        let eb = *p2;
                        let ec = *p3;
                        if m.clone() == ma.clone() &&
                             <Exp as Equal>::equal(e.clone(), eb.clone()) {
                            bind(
                                append_o_o_i(ea.clone()),
                                (({
                                    let ec_cap = ec.clone();
                                    let ct_cap = ct.clone();
                                    Rc::new(move |aa: (List<Exp>, List<Exp>)| -> Pred<Unit> {
                                        match aa.clone() {
    (_, List::Nil) =>
        bot_pred::<Unit>(),
    (el, List::Cons (ei, p0)) =>
        {
            let er = *p0;
            bind(
                reduce(ct_cap.clone(), ei.clone()),
                (({
                    let ec_capa = ec_cap.clone();
                    let er_cap = er.clone();
                    let el_cap = el.clone();
                    Rc::new(move |xc: Exp| -> Pred<Unit> {
                        bind(
                            append_i_i_i(el_cap.clone(), List::Cons (xc.clone(), Box::new(er_cap.clone())), ec_capa.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(Exp) -> Pred<Unit>>)
            )
        },
    _ =>
        panic!("non-exhaustive match")
}
                                    })
                                }) as Rc<dyn Fn((List<Exp>, List<Exp>)) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                (_, (Exp::MethodInvk (_, _, _), Exp::New (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), Exp::Cast (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (_, (Exp::Var (_), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), Exp::Var (_))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), Exp::FieldProj (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<Unit>(),
                (ct, (Exp::New (c, p0), Exp::New (ca, p1))) =>
                    {
                        let ea = *p0;
                        let e = *p1;
                        if c.clone() == ca.clone() {
                            bind(
                                append_o_o_i(ea.clone()),
                                (({
                                    let e_cap = e.clone();
                                    let ct_cap = ct.clone();
                                    Rc::new(move |aa: (List<Exp>, List<Exp>)| -> Pred<Unit> {
                                        match aa.clone() {
    (_, List::Nil) =>
        bot_pred::<Unit>(),
    (el, List::Cons (ei, p0)) =>
        {
            let er = *p0;
            bind(
                reduce(ct_cap.clone(), ei.clone()),
                (({
                    let e_capa = e_cap.clone();
                    let er_cap = er.clone();
                    let el_cap = el.clone();
                    Rc::new(move |xc: Exp| -> Pred<Unit> {
                        bind(
                            append_i_i_i(el_cap.clone(), List::Cons (xc.clone(), Box::new(er_cap.clone())), e_capa.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(Exp) -> Pred<Unit>>)
            )
        },
    _ =>
        panic!("non-exhaustive match")
}
                                    })
                                }) as Rc<dyn Fn((List<Exp>, List<Exp>)) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                (_, (Exp::New (_, _), Exp::Cast (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            match a.clone() {
                (_, (Exp::Var (_), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::FieldProj (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::MethodInvk (_, _, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::New (_, _), _)) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), Exp::Var (_))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), Exp::FieldProj (_, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), Exp::MethodInvk (_, _, _))) =>
                    bot_pred::<Unit>(),
                (_, (Exp::Cast (_, _), Exp::New (_, _))) =>
                    bot_pred::<Unit>(),
                (ct, (Exp::Cast (c, p0), Exp::Cast (ca, p1))) =>
                    {
                        let e0 = *p0;
                        let e0a = *p1;
                        if c.clone() == ca.clone() {
                            bind(
                                reduction_i_i_i(ct.clone(), e0.clone(), e0a.clone()),
                                ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    single(Unit::Unity)
                                })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        } else {
                            bot_pred::<Unit>()
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ))))))))
}

pub fn typings_i_i_i_i
    (xa: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xb: Rc<dyn Fn(BigInt) -> Option<BigInt>>, xc: List<Exp>,
      xd: List<BigInt>) -> Pred<Unit> {
    sup_pred(bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (List<Exp>, List<BigInt>)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (List::Nil, List::Nil))) =>
                    single(Unit::Unity),
                (_, (_, (List::Nil, List::Cons (_, _)))) =>
                    bot_pred::<Unit>(),
                (_, (_, (List::Cons (_, _), _))) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (List<Exp>, List<BigInt>)))) -> Pred<Unit>>)
    ), bind(
        single((xa.clone(), (xb.clone(), (xc.clone(), xd.clone())))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (List<Exp>, List<BigInt>)))| -> Pred<Unit> {
            match a.clone() {
                (_, (_, (List::Nil, _))) =>
                    bot_pred::<Unit>(),
                (_, (_, (List::Cons (_, _), List::Nil))) =>
                    bot_pred::<Unit>(),
                (ct, (gamma, (List::Cons (e0, p0), List::Cons (c0, p1)))) =>
                    {
                        let es = *p0;
                        let cs = *p1;
                        bind(
                            typings_i_i_i_i(ct.clone(), gamma.clone(), es.clone(), cs.clone()),
                            (({
                                let c0_cap = c0.clone();
                                let e0_cap = e0.clone();
                                let gamma_cap = gamma.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    bind(
                                        typing_i_i_i_i(ct_cap.clone(), gamma_cap.clone(), e0_cap.clone(), c0_cap.clone()),
((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    single(Unit::Unity)
})) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Rc<dyn Fn(BigInt) -> Option<BigInt>>, (List<Exp>, List<BigInt>)))) -> Pred<Unit>>)
    ))
}

pub fn method_typing_aux_i_i_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: BigInt, xb: BigInt,
      xc: List<BigInt>, xd: BigInt) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (d, (cs, _)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))| -> Pred<Unit> {
            bind(
                mtype_i_i_i_o_o(ct.clone(), m.clone(), d.clone()),
                (({
                    let cs_cap = cs.clone();
                    Rc::new(move |(ds, _): (List<BigInt>, BigInt)| -> Pred<Unit> {
                        bind(
                            if_pred(! <List<BigInt> as Equal>::equal(cs_cap.clone(), ds.clone())),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn((List<BigInt>, BigInt)) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), (xb.clone(), (xc.clone(), xd.clone()))))),
        ((Rc::new(move |(ct, (m, (d, (_, c)))): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))| -> Pred<Unit> {
            bind(
                mtype_i_i_i_o_o(ct.clone(), m.clone(), d.clone()),
                (({
                    let c_cap = c.clone();
                    Rc::new(move |(_, d0): (List<BigInt>, BigInt)| -> Pred<Unit> {
                        bind(
                            if_pred(! (c_cap.clone() == d0.clone())),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn((List<BigInt>, BigInt)) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (BigInt, (BigInt, (List<BigInt>, BigInt))))) -> Pred<Unit>>)
    ))
}

pub fn method_typing_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: MethodDefExt<Unit>,
      xb: BigInt) -> Pred<Unit> {
    bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (mDef, c)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (MethodDefExt<Unit>, BigInt))| -> Pred<Unit> {
            bind(
                eq_i_o((*ct)(c.clone())),
                (({
                    let ct_cap = ct.clone();
                    let mDef_cap = mDef.clone();
                    let c_cap = c.clone();
                    Rc::new(move |a: Option<ClassDefExt<Unit>>| -> Pred<Unit> {
                        match a.clone() {
                            Option::None =>
                                bot_pred::<Unit>(),
                            Option::Some (cDef) =>
                                bind(
                                    eq_i_i(c_name(cDef.clone()), c_cap.clone()),
                                    (({
                                        let c_capa = c_cap.clone();
let ct_capa = ct_cap.clone();
let mDef_capa = mDef_cap.clone();
let cDef_cap = cDef.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    bind(
        eq_i_o(c_super(cDef_cap.clone())),
        (({
            let c_capb = c_capa.clone();
            let ct_capb = ct_capa.clone();
            let cDef_capa = cDef_cap.clone();
            let mDef_capb = mDef_capa.clone();
            Rc::new(move |xc: BigInt| -> Pred<Unit> {
                bind(
                    eq_i_o(m_name(mDef_capb.clone())),
                    (({
                        let c_capc = c_capb.clone();
                        let x_cap = xc.clone();
                        let ct_capc = ct_capb.clone();
                        let mDef_capc = mDef_capb.clone();
                        let cDef_capb = cDef_capa.clone();
                        Rc::new(move |xaa: BigInt| -> Pred<Unit> {
                            bind(
                                eq_i_i(lookup(
                                    c_methods(cDef_capb.clone()),
                                    (({
                                        let xa_cap = xaa.clone();
Rc::new(move |md: MethodDefExt<Unit>| -> bool {
    m_name(md.clone()) == xa_cap.clone()
})
                                    }) as Rc<dyn Fn(MethodDefExt<Unit>) -> bool>)
                                ), Option::Some (mDef_capc.clone())),
                                (({
                                    let c_capd = c_capc.clone();
                                    let x_capa = x_cap.clone();
                                    let xa_cap = xaa.clone();
                                    let ct_capd = ct_capc.clone();
                                    let mDef_capd = mDef_capc.clone();
                                    Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                        bind(
    eq_i_o(m_return(mDef_capd.clone())),
    (({
        let c_cape = c_capd.clone();
        let x_capb = x_capa.clone();
        let xa_capa = xa_cap.clone();
        let ct_cape = ct_capd.clone();
        let mDef_cape = mDef_capd.clone();
        Rc::new(move |xba: BigInt| -> Pred<Unit> {
            bind(
                eq_i_o(m_params(mDef_cape.clone())),
                (({
                    let c_capf = c_cape.clone();
                    let xb_cap = xba.clone();
                    let x_capc = x_capb.clone();
                    let xa_capb = xa_capa.clone();
                    let ct_capf = ct_cape.clone();
                    let mDef_capf = mDef_cape.clone();
                    Rc::new(move |xca: List<VarDefExt<Unit>>| -> Pred<Unit> {
                        bind(
                            eq_i_o(m_body(mDef_capf.clone())),
                            (({
                                let c_capg = c_capf.clone();
                                let xb_capa = xb_cap.clone();
                                let x_capd = x_capc.clone();
                                let xa_capc = xa_capb.clone();
                                let ct_capg = ct_capf.clone();
                                let xc_cap = xca.clone();
                                Rc::new(move |xd: Exp| -> Pred<Unit> {
                                    bind(
                                        eq_i_o(var_defs_types(xc_cap.clone())),
(({
    let xd_cap = xd.clone();
    let c_caph = c_capg.clone();
    let xc_capa = xc_cap.clone();
    let xb_capb = xb_capa.clone();
    let x_cape = x_capd.clone();
    let xa_capd = xa_capc.clone();
    let ct_caph = ct_capg.clone();
    Rc::new(move |xe: List<BigInt>| -> Pred<Unit> {
        bind(
            not_pred(method_typing_aux_i_i_i_i_i(ct_caph.clone(), xa_capd.clone(), x_cape.clone(), xe.clone(), xb_capb.clone())),
            (({
                let xb_capc = xb_capb.clone();
                let xd_capa = xd_cap.clone();
                let ct_capi = ct_caph.clone();
                let c_capi = c_caph.clone();
                let xe_cap = xe.clone();
                let xc_capb = xc_capa.clone();
                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                    bind(
                        eq_i_o(var_defs_names(xc_capb.clone())),
                        (({
                            let xb_capd = xb_capc.clone();
                            let xd_capb = xd_capa.clone();
                            let ct_capj = ct_capi.clone();
                            let c_capj = c_capi.clone();
                            let xe_capa = xe_cap.clone();
                            Rc::new(move |xf: List<BigInt>| -> Pred<Unit> {
                                bind(
                                    eq_o_i((({
                                        let c_capk = c_capj.clone();
let xe_capb = xe_capa.clone();
let x_capf = xf.clone();
Rc::new(move |aa: BigInt| -> Option<BigInt> {
    (*fun_upd((({
        let xe_capc = xe_capb.clone();
        let x_capg = x_capf.clone();
        Rc::new(move |ab: BigInt| -> Option<BigInt> {
            (*map_upds(
                ((Rc::new(move |_: BigInt| -> Option<BigInt> {
                    Option::None
                })) as Rc<dyn Fn(BigInt) -> Option<BigInt>>),
                x_capg.clone(),
                xe_capc.clone()
            ))(ab.clone())
        })
    }) as Rc<dyn Fn(BigInt) -> Option<BigInt>>), this(), Option::Some (c_capk.clone())))(aa.clone())
})
                                    }) as Rc<dyn Fn(BigInt) -> Option<BigInt>>)),
                                    (({
                                        let xb_cape = xb_capd.clone();
let xd_capc = xd_capb.clone();
let ct_capk = ct_capj.clone();
Rc::new(move |xg: Rc<dyn Fn(BigInt) -> Option<BigInt>>| -> Pred<Unit> {
    bind(
        typing_i_i_i_o(ct_capk.clone(), xg.clone(), xd_capc.clone()),
        (({
            let xb_capf = xb_cape.clone();
            let ct_capl = ct_capk.clone();
            Rc::new(move |xh: BigInt| -> Pred<Unit> {
                bind(
                    subtyping_i_i_i(ct_capl.clone(), xh.clone(), xb_capf.clone()),
                    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                        single(Unit::Unity)
                    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(Rc<dyn Fn(BigInt) -> Option<BigInt>>) -> Pred<Unit>>)
                                )
                            })
                        }) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
                    )
                })
            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
        )
    })
}) as Rc<dyn Fn(List<BigInt>) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(Exp) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
            )
        })
    }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                            )
                        })
                    }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                ),
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    })
                }) as Rc<dyn Fn(Option<ClassDefExt<Unit>>) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (MethodDefExt<Unit>, BigInt))) -> Pred<Unit>>)
    )
}

pub fn method_typings_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xa: List<MethodDefExt<Unit>>, xb: BigInt) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<MethodDefExt<Unit>>, BigInt))| -> Pred<Unit> {
            match a.clone() {
                (_, (List::Nil, _)) =>
                    single(Unit::Unity),
                (_, (List::Cons (_, _), _)) =>
                    bot_pred::<Unit>(),
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<MethodDefExt<Unit>>, BigInt))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |a: (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<MethodDefExt<Unit>>, BigInt))| -> Pred<Unit> {
            match a.clone() {
                (_, (List::Nil, _)) =>
                    bot_pred::<Unit>(),
                (ct, (List::Cons (m, p0), c)) =>
                    {
                        let ms = *p0;
                        bind(
                            method_typings_i_i_i(ct.clone(), ms.clone(), c.clone()),
                            (({
                                let c_cap = c.clone();
                                let m_cap = m.clone();
                                let ct_cap = ct.clone();
                                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                    bind(
                                        method_typing_i_i_i(ct_cap.clone(), m_cap.clone(), c_cap.clone()),
((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    single(Unit::Unity)
})) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (List<MethodDefExt<Unit>>, BigInt))) -> Pred<Unit>>)
    ))
}

pub fn class_typing_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      xa: ClassDefExt<Unit>) -> Pred<Unit> {
    bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(ct, cDef): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, ClassDefExt<Unit>)| -> Pred<Unit> {
            bind(
                eq_i_o(c_name(cDef.clone())),
                (({
                    let ct_cap = ct.clone();
                    let cDef_cap = cDef.clone();
                    Rc::new(move |xb: BigInt| -> Pred<Unit> {
                        bind(
                            eq_i_o(c_super(cDef_cap.clone())),
                            (({
                                let ct_capa = ct_cap.clone();
                                let x_cap = xb.clone();
                                let cDef_capa = cDef_cap.clone();
                                Rc::new(move |xaa: BigInt| -> Pred<Unit> {
                                    bind(
                                        eq_i_o(c_constructor(cDef_capa.clone())),
(({
    let xa_cap = xaa.clone();
    let ct_capb = ct_capa.clone();
    let cDef_capb = cDef_capa.clone();
    let x_capa = x_cap.clone();
    Rc::new(move |xba: ConstructorDefExt<Unit>| -> Pred<Unit> {
        bind(
            eq_i_i(k_name(xba.clone()), x_capa.clone()),
            (({
                let xb_cap = xba.clone();
                let xa_capa = xa_cap.clone();
                let x_capb = x_capa.clone();
                let ct_capc = ct_capb.clone();
                let cDef_capc = cDef_capb.clone();
                Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                    bind(
                        eq_i_o(c_methods(cDef_capc.clone())),
                        (({
                            let xb_capa = xb_cap.clone();
                            let xa_capb = xa_capa.clone();
                            let x_capc = x_capb.clone();
                            let ct_capd = ct_capc.clone();
                            Rc::new(move |xc: List<MethodDefExt<Unit>>| -> Pred<Unit> {
                                bind(
                                    method_typings_i_i_i(ct_capd.clone(), xc.clone(), x_capc.clone()),
                                    (({
                                        let xb_capb = xb_capa.clone();
let xa_capc = xa_capb.clone();
let ct_cape = ct_capd.clone();
Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
    bind(
        fields_i_i_o(ct_cape.clone(), xa_capc.clone()),
        (({
            let xb_capc = xb_capb.clone();
            Rc::new(move |xd: List<VarDefExt<Unit>>| -> Pred<Unit> {
                bind(
                    eq_i_i(k_super(xb_capc.clone()), var_defs_names(xd.clone())),
                    (({
                        let xb_capd = xb_capc.clone();
                        let x_capd = xd.clone();
                        Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                            bind(
                                append_i_o_i(x_capd.clone(), k_params(xb_capd.clone())),
                                (({
                                    let xb_cape = xb_capd.clone();
                                    Rc::new(move |xe: List<VarDefExt<Unit>>| -> Pred<Unit> {
                                        bind(
    eq_i_i(k_inits(xb_cape.clone()), var_defs_names(xe.clone())),
    ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
        single(Unit::Unity)
    })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
)
                                    })
                                }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
                            )
                        })
                    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                )
            })
        }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Pred<Unit>>)
    )
})
                                    }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                                )
                            })
                        }) as Rc<dyn Fn(List<MethodDefExt<Unit>>) -> Pred<Unit>>)
                    )
                })
            }) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
        )
    })
}) as Rc<dyn Fn(ConstructorDefExt<Unit>) -> Pred<Unit>>)
                                    )
                                })
                            }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(BigInt) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, ClassDefExt<Unit>)) -> Pred<Unit>>)
    )
}

pub fn reductions_i_i_i
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: Exp,
      xb: Exp) -> Pred<Unit> {
    sup_pred(bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(_, (e, ea)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            if <Exp as Equal>::equal(e.clone(), ea.clone()) {
                single(Unit::Unity)
            } else {
                bot_pred::<Unit>()
            }
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ), bind(
        single((x.clone(), (xa.clone(), xb.clone()))),
        ((Rc::new(move |(ct, (e, ea)): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))| -> Pred<Unit> {
            bind(
                reduce(ct.clone(), e.clone()),
                (({
                    let ea_cap = ea.clone();
                    let ct_cap = ct.clone();
                    Rc::new(move |xc: Exp| -> Pred<Unit> {
                        bind(
                            reductions_i_i_i(ct_cap.clone(), xc.clone(), ea_cap.clone()),
                            ((Rc::new(move |Unit::Unity: Unit| -> Pred<Unit> {
                                single(Unit::Unity)
                            })) as Rc<dyn Fn(Unit) -> Pred<Unit>>)
                        )
                    })
                }) as Rc<dyn Fn(Exp) -> Pred<Unit>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, (Exp, Exp))) -> Pred<Unit>>)
    ))
}

pub fn reductions_i_i_o
    (x: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, xa: Exp) -> Pred<Exp> {
    sup_pred(bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(_, a): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            single(a.clone())
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ), bind(
        single((x.clone(), xa.clone())),
        ((Rc::new(move |(ct, e): (Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)| -> Pred<Exp> {
            bind(
                reduce(ct.clone(), e.clone()),
                (({
                    let ct_cap = ct.clone();
                    Rc::new(move |xb: Exp| -> Pred<Exp> {
                        bind(reductions_i_i_o(ct_cap.clone(), xb.clone()), ((Rc::new(move |a: Exp| -> Pred<Exp> {
                            single(a.clone())
                        })) as Rc<dyn Fn(Exp) -> Pred<Exp>>))
                    })
                }) as Rc<dyn Fn(Exp) -> Pred<Exp>>)
            )
        })) as Rc<dyn Fn((Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, Exp)) -> Pred<Exp>>)
    ))
}

pub fn method_typing_aux
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: BigInt,
      x3: BigInt, x4: List<BigInt>, x5: BigInt) -> bool {
    holds(method_typing_aux_i_i_i_i_i(x1.clone(), x2.clone(), x3.clone(), x4.clone(), x5.clone()))
}
