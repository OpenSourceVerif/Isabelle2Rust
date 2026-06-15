#[derive(Clone)]
pub enum Peano { 
  Za, 
  S (Box<Peano>)
}

pub fn grow  (n: Peano) -> Peano
                {
               {
                 let x = n.clone();
                 let xa = Peano::S (Box::new(x.clone()));
                 let xb = Peano::S (Box::new(xa.clone()));
                 xb.clone()
               }
             }
