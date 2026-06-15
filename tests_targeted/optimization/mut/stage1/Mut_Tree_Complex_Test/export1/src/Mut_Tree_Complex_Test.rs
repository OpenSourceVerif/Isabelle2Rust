#[derive(Clone)]
pub enum MutTree { 
  MTLeaf (bool), 
  MTNode (Box<MutTree>, Box<MutTree>)
}

pub fn mtree_mirror 
  (x0: MutTree) -> MutTree
     {
    match x0 {
      MutTree::MTLeaf (b) => MutTree::MTLeaf (b.clone()), 
      MutTree::MTNode
                 (box l,
                   box r) => MutTree::MTNode
(Box::new(mtree_mirror(r.clone())), Box::new(mtree_mirror(l.clone())))
    }
  }

pub fn mtree_set_all 
  (b: bool, x1: MutTree) -> MutTree
     {
    match (b, x1) {
      (b, MutTree::MTLeaf (uu)) => MutTree::MTLeaf (b.clone()), 
      (b, MutTree::MTNode
                     (box l,
                       box r)) => MutTree::MTNode
     (Box::new(mtree_set_all(b.clone(), l.clone())),
       Box::new(mtree_set_all(b.clone(), r.clone())))
    }
  }

pub fn mtree_any_label 
  (x0: MutTree) -> bool
     {
    match x0 {
      MutTree::MTLeaf (b) => b.clone(), 
      MutTree::MTNode
                 (box l,
                   box r) => mtree_any_label(l.clone()) ||
                               mtree_any_label(r.clone())
    }
  }

pub fn mtree_flip_labels 
  (x0: MutTree) -> MutTree
     {
    match x0 {
      MutTree::MTLeaf (b) => MutTree::MTLeaf (! b.clone()), 
      MutTree::MTNode
                 (box l,
                   box r) => MutTree::MTNode
(Box::new(mtree_flip_labels(l.clone())), Box::new(mtree_flip_labels(r.clone())))
    }
  }

pub fn mtree_two_chains 
  (t: MutTree, u: MutTree) -> MutTree
     {
    {
      let x = t.clone();
      let y = u.clone();
      let xa = mtree_mirror(x.clone());
      let a = mtree_flip_labels(y.clone());
      MutTree::MTNode (Box::new(xa.clone()), Box::new(a.clone()))
    }
  }

pub fn mtree_rebuild_chain  (t: MutTree) -> MutTree
                               {
                              {
                                let x = t.clone();
                                let xa = mtree_flip_labels(x.clone());
                                let xb = mtree_mirror(xa.clone());
                                let xc = mtree_set_all(true, xb.clone());
                                xc.clone()
                              }
                            }

pub fn mtree_branch_rhs_chain 
  (flag: bool, t: MutTree) -> MutTree
     {
    {
      let x = t.clone();
      let xa = match flag.clone() {
                 true => mtree_mirror(x.clone()), 
                 false => mtree_flip_labels(x.clone())
               };
      let xb = mtree_set_all(flag.clone(), xa.clone());
      xb.clone()
    }
  }

pub fn mtree_interleaved_chain 
  (seed: bool, t: MutTree) -> MutTree
     {
    {
      let x = t.clone();
      let mark = seed.clone();
      let xa = mtree_set_all(mark.clone(), x.clone());
      let marka = ! mark.clone();
      let xb = mtree_set_all(marka.clone(), mtree_mirror(xa.clone()));
      xb.clone()
    }
  }

pub fn mtree_saved_value_blocks_chain 
  (t: MutTree) -> MutTree
     {
    {
      let x = t.clone();
      let saved = x.clone();
      let a = mtree_mirror(x.clone());
      MutTree::MTNode (Box::new(saved.clone()), Box::new(a.clone()))
    }
  }
