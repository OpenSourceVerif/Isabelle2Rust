#[derive(Clone)]
pub enum Tree { 
  Leaf (bool), 
  Branch (Box<Tree>, Box<Tree>)
}

pub fn rebuild 
  (x0: Tree) -> Tree
     {
    match x0 {
      Tree::Leaf (b) => Tree::Leaf (b.clone()), 
      Tree::Branch
              (box l,
                box r) => Tree::Branch
                                  (Box::new(rebuild(l.clone())),
                                    Box::new(rebuild(r.clone())))
    }
  }

pub fn any_label 
  (x0: Tree) -> bool
     {
    match x0 {
      Tree::Leaf (b) => b.clone(), 
      Tree::Branch
              (box l, box r) => any_label(l.clone()) || any_label(r.clone())
    }
  }

pub fn any_label_twice  (t: Tree) -> bool
                           {
                          any_label(t.clone()) && any_label(t.clone())
                        }
