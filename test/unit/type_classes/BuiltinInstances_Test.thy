theory BuiltinInstances_Test
  imports Main "Rust.Rust_Setup"
begin

(* Built-in classes still need reconstructed Rust traits and impls.
   This file keeps the cases where the class is introduced by HOL libraries,
   rather than by a user-defined class declaration in the test. *)

datatype color = Red | Green | Blue

(* Function update depends on equality for the key type. *)
definition set_color :: "(color \<Rightarrow> nat) \<Rightarrow> color \<Rightarrow> nat \<Rightarrow> (color \<Rightarrow> nat)" where
  "set_color f c n = f(c := n)"

(* Equality for a nominal datatype requires a concrete Equal impl. *)
definition eq_color :: "color \<Rightarrow> color \<Rightarrow> bool" where
  "eq_color a b = (a = b)"

(* Tuple equality uses the tuple mixfix syntax, not a nominal Pair receiver. *)
definition eq_pair :: "nat \<times> nat \<Rightarrow> bool" where
  "eq_pair p = (p = (0, 0))"

(* Nested type constructors should compose their derived equality instances. *)
definition eq_nested :: "color option \<Rightarrow> color option \<Rightarrow> bool" where
  "eq_nested x y = (x = y)"

(* int zero is a code datatype constructor, so the Zero impl must return it
   through trait dispatch instead of calling a generated zero_int body. *)
definition pick :: "bool \<Rightarrow> 'a::zero_neq_one" where
  "pick b = of_bool b"

definition pick_int :: "bool \<Rightarrow> int" where
  "pick_int b = pick b"

export_code
  set_color eq_color eq_pair eq_nested pick_int
  in Rust

end
