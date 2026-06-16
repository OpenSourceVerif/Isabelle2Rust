use crate::Product_Type::Prod;

#[derive(Clone)]
pub enum LuTree { 
  LULeaf (bool), 
  LUNode (Box<LuTree>, Box<LuTree>)
}

pub fn lu_flip 
  (x0: LuTree) -> LuTree
     {
    match x0 {
      LuTree::LULeaf (b) => LuTree::LULeaf (! b.clone()), 
      LuTree::LUNode
                (box l,
                  box r) => LuTree::LUNode
                                      (Box::new(lu_flip(l.clone())),
Box::new(lu_flip(r.clone())))
    }
  }

pub fn lu_pair  (t: LuTree) -> Prod<LuTree, LuTree>
                   {
                  Prod::Pair (t.clone(), t.clone())
                }

pub fn lu_wrap 
  (t: LuTree) -> LuTree
     {
    LuTree::LUNode (Box::new(LuTree::LULeaf (true)), Box::new(t.clone()))
  }

pub fn lu_pair2  (l: LuTree, r: LuTree) -> Prod<LuTree, LuTree>
                    {
                   Prod::Pair (l.clone(), r.clone())
                 }

pub fn lu_triple  (t: LuTree) -> Prod<LuTree, Prod<LuTree, LuTree>>
                     {
                    Prod::Pair (t.clone(), Prod::Pair (t.clone(), t.clone()))
                  }

pub fn lu_chain_then_pair  (t: LuTree) -> Prod<LuTree, LuTree>
                              {
                             {
                               let x = t.clone();
                               let xa = lu_wrap(x.clone());
                               let a = lu_flip(xa.clone());
                               lu_pair(a.clone())
                             }
                           }

pub fn lu_second_arg_last_use  (t: LuTree) -> Prod<LuTree, LuTree>
                                  {
                                 lu_pair2(t.clone(), t.clone())
                               }
