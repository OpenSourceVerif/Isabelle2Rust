use crate::Product_Type::Prod;

#[derive(Clone)]
pub enum MutWrap<A> { 
  MutWrap (A)
}

#[derive(Clone)]
pub enum MutPairBox<A> { 
  MutPairBox (A, A)
}

pub fn wrap_dup <A> (x: MutWrap<A>) -> Prod<MutWrap<A>, MutWrap<A>>
                      where
                        A : Clone + 'static
                       {
                      Prod::Pair (x.clone(), x.clone())
                    }

pub fn wrap_rebuild <A>
  (x0: MutWrap<A>) -> MutWrap<A>
    where
      A : Clone + 'static
     {
    match x0{MutWrap::MutWrap (x) => MutWrap::MutWrap (x.clone())}
  }

pub fn wrap_chain <A> (w: MutWrap<A>) -> MutWrap<A>
                        where
                          A : Clone + 'static
                         {
                        {
                          let x = w.clone();
                          let xa = wrap_rebuild(x.clone());
                          let xb = wrap_rebuild(xa.clone());
                          xb.clone()
                        }
                      }

pub fn pair_box_swap <A>
  (x0: MutPairBox<A>) -> MutPairBox<A>
    where
      A : Clone + 'static
     {
    match x0{MutPairBox::MutPairBox
                           (x, y) => MutPairBox::MutPairBox
           (y.clone(), x.clone())}
  }

pub fn pair_box_keep_left <A>
  (x0: MutPairBox<A>) -> MutPairBox<A>
    where
      A : Clone + 'static
     {
    match x0{MutPairBox::MutPairBox
                           (x, y) => MutPairBox::MutPairBox
           (x.clone(), x.clone())}
  }

pub fn pair_box_chain <A> (p: MutPairBox<A>) -> MutPairBox<A>
                            where
                              A : Clone + 'static
                             {
                            {
                              let x = p.clone();
                              let xa = pair_box_swap(x.clone());
                              let xb = pair_box_keep_left(xa.clone());
                              xb.clone()
                            }
                          }

pub fn nested_wrap_chain <A> (w: MutWrap<MutWrap<A>>) -> MutWrap<MutWrap<A>>
                               where
                                 A : Clone + 'static
                                {
                               {
                                 let x = w.clone();
                                 let xa = wrap_rebuild(x.clone());
                                 let xb = wrap_rebuild(xa.clone());
                                 xb.clone()
                               }
                             }

pub fn wrap_chain_then_dup <A> (w: MutWrap<A>) -> Prod<MutWrap<A>, MutWrap<A>>
                                 where
                                   A : Clone + 'static
                                  {
                                 {
                                   let x = w.clone();
                                   let a = wrap_rebuild(x.clone());
                                   wrap_dup(a.clone())
                                 }
                               }

pub fn wrap_saved_value_blocks_chain <A>
  (w: MutWrap<A>) -> Prod<MutWrap<A>, MutWrap<A>>
    where
      A : Clone + 'static
     {
    {
      let x = w.clone();
      let saved = x.clone();
      let a = wrap_rebuild(x.clone());
      Prod::Pair (saved.clone(), a.clone())
    }
  }
