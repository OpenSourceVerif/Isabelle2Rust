theory ClassMethods_Test
  imports Main "Rust.Rust_Setup"
begin

(* Class operations become receiver-free static trait functions. *)

class inc =
  fixes inc :: "'a \<Rightarrow> 'a"

fun inc1 :: "('a::inc) \<Rightarrow> 'a" where
  "inc1 x = inc x"

class combine =
  fixes combine :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun combine3 :: "('a::combine) \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> 'a" where
  "combine3 x y z = combine (combine x y) z"

class chooser =
  fixes pick_method :: "bool \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun choose2 :: "('a::chooser) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "choose2 x y = pick_method True x y"

class twoop =
  fixes op1 :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "<+>" 65)
    and op2 :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "<*>" 65)

fun twoop_chain :: "('a::twoop) \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> 'a" where
  "twoop_chain a b c = (a <+> b) <*> c"

export_code
  inc1 combine3 choose2 twoop_chain
  in Rust

end
