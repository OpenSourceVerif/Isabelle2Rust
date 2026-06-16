use crate::Product_Type::Prod;

#[derive(Clone)]
pub enum MutColor { 
  MRed, 
  MGreen, 
  MBlue
}

pub fn color_next  (x0: MutColor) -> MutColor
                      {
                     match x0 {
                       MutColor::MRed => MutColor::MGreen, 
                       MutColor::MGreen => MutColor::MBlue, 
                       MutColor::MBlue => MutColor::MRed
                     }
                   }

pub fn color_tint  (x0: bool, c: MutColor) -> MutColor
                      {
                     match (x0, c) {
                       (true, c) => c.clone(), 
                       (false, c) => color_next(c.clone())
                     }
                   }

pub fn color_step  (flag: bool, c: MutColor) -> MutColor
                      {
                     color_tint(flag.clone(), color_next(c.clone()))
                   }

pub fn color_adjacent_chain  (c: MutColor) -> MutColor
                                {
                               {
                                 let x = c.clone();
                                 let xa = color_next(x.clone());
                                 let xb = color_tint(true, xa.clone());
                                 xb.clone()
                               }
                             }

pub fn color_call_rhs_chain 
  (flag: bool, c: MutColor) -> MutColor
     {
    {
      let x = c.clone();
      let xa = color_step(flag.clone(), x.clone());
      let xb = color_step(! flag.clone(), xa.clone());
      xb.clone()
    }
  }

pub fn color_interleaved_chain 
  (seed: bool, c: MutColor) -> MutColor
     {
    {
      let x = c.clone();
      let flag = seed.clone();
      let xa = color_tint(flag.clone(), x.clone());
      let flaga = ! flag.clone();
      let xb = color_tint(flaga.clone(), color_next(xa.clone()));
      xb.clone()
    }
  }

pub fn color_saved_value_blocks_chain  (c: MutColor) -> Prod<MutColor, MutColor>
  {
 {
   let x = c.clone();
   let saved = x.clone();
   let a = color_next(x.clone());
   Prod::Pair (saved.clone(), a.clone())
 }
                                       }
