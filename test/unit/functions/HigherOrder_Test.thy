theory HigherOrder_Test
  imports Main "Rust.Rust_Setup"
begin

(* Function-typed parameters and results carry Clone/static bounds. *)

class my_cls =
  fixes my_op :: "'a \<Rightarrow> 'a"

definition apply_first :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "apply_first g x = g (my_op x)"

definition call_apply_first :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "call_apply_first f x = apply_first f x"

definition apply_twice :: "('a \<Rightarrow> 'a) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "apply_twice f x = f (f x)"

definition compose :: "('b \<Rightarrow> 'c) \<Rightarrow> ('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'c" where
  "compose f g x = f (g x)"

definition make_adder :: "int \<Rightarrow> int \<Rightarrow> int" where
  "make_adder n = (\<lambda>x. x + n)"

definition apply_generated :: "int \<Rightarrow> int \<Rightarrow> int" where
  "apply_generated n x = make_adder n x"

definition choose_fun :: "bool \<Rightarrow> ('a \<Rightarrow> 'a) \<Rightarrow> ('a \<Rightarrow> 'a) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "choose_fun b f g x = (if b then f x else g x)"

export_code
  call_apply_first apply_twice compose apply_generated choose_fun
  in Rust

end
