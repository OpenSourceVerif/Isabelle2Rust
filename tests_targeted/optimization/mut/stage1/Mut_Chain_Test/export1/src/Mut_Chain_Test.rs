#[derive(Clone)]
pub enum Peano { 
  Za, 
  S (Box<Peano>)
}

pub fn bump  (n: Peano) -> Peano
                {
               Peano::S (Box::new(Peano::S (Box::new(n.clone()))))
             }

pub fn grow  (n: Peano) -> Peano
                {
               {
                 let x = n.clone();
                 let xa = Peano::S (Box::new(x.clone()));
                 let xb = bump(xa.clone());
                 let xc = Peano::S (Box::new(xb.clone()));
                 xc.clone()
               }
             }
