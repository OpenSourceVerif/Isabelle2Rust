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

pub fn lu_pair 
  (t: LuTree) -> crate::Product_Type::Prod<LuTree, LuTree>
     {
    match t{t => crate::Product_Type::Prod::Pair (t.clone(), t.clone())}
  }

pub fn lu_wrap 
  (t: LuTree) -> LuTree
     {
    match t{t => LuTree::LUNode
                           (Box::new(LuTree::LULeaf (true)),
                             Box::new(t.clone()))}
  }

pub fn lu_pair2 
  (l: LuTree, r: LuTree) -> crate::Product_Type::Prod<LuTree, LuTree>
     {
    match (l, r){(l, r) => crate::Product_Type::Prod::Pair
                (l.clone(), r.clone())}
  }

pub fn lu_triple 
  (t: LuTree) -> crate::Product_Type::Prod<LuTree,
     crate::Product_Type::Prod<LuTree, LuTree>>
     {
    match t{t => crate::Product_Type::Prod::Pair
      (t.clone(), crate::Product_Type::Prod::Pair (t.clone(), t.clone()))}
  }

pub fn lu_chain_then_pair 
  (t: LuTree) -> crate::Product_Type::Prod<LuTree, LuTree>
     {
    {
      let x = t.clone();
      let xa = lu_wrap(x.clone());
      let a = lu_flip(xa.clone());
      lu_pair(a.clone())
    }
  }

pub fn lu_second_arg_last_use 
  (t: LuTree) -> crate::Product_Type::Prod<LuTree, LuTree>
     {
    match t{t => lu_pair2(t.clone(), t.clone())}
  }
