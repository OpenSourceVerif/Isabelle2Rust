#[derive(Clone)]
pub enum BorrowBox<A> { 
  BorrowBox (A)
}

#[derive(Clone)]
pub enum BorrowTree { 
  BLeaf (bool), 
  BNode (Box<BorrowTree>, Box<BorrowTree>)
}

pub fn bbox_dup <A>
  (x: BorrowBox<A>) -> crate::Product_Type::Prod<BorrowBox<A>, BorrowBox<A>>
    where
      A : Clone
     {
    match x{x => crate::Product_Type::Prod::Pair (x.clone(), x.clone())}
  }

pub fn bbox_get <A> (x0: BorrowBox<A>) -> A
                      where
                        A : Clone
                       {
                      match x0{BorrowBox::BorrowBox (x) => x.clone()}
                    }

pub fn bbox_swap <A>
  (x: BorrowBox<A>,
    y: BorrowBox<A>) -> crate::Product_Type::Prod<BorrowBox<A>, BorrowBox<A>>
    where
      A : Clone
     {
    match (x, y){(x, y) => crate::Product_Type::Prod::Pair
                (y.clone(), x.clone())}
  }

pub fn btree_dup 
  (x: BorrowTree) -> crate::Product_Type::Prod<BorrowTree, BorrowTree>
     {
    match x{x => crate::Product_Type::Prod::Pair (x.clone(), x.clone())}
  }

pub fn btree_is_leaf  (x0: BorrowTree) -> bool
                         {
                        match x0 {
                          BorrowTree::BLeaf (uu) => true, 
                          BorrowTree::BNode (box uv, box uw) => false
                        }
                      }

pub fn btree_leaf_val  (x0: BorrowTree) -> bool
                          {
                         match x0 {
                           BorrowTree::BLeaf (b) => b.clone(), 
                           BorrowTree::BNode (box uu, box uv) => false
                         }
                       }
