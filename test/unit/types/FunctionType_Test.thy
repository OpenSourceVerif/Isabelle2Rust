theory FunctionType_Test
  imports Main "Rust.Rust_Setup"
begin

fun apply_twice_int :: "(int \<Rightarrow> int) \<Rightarrow> int \<Rightarrow> int" where
  "apply_twice_int f x = f (f x)"

fun apply_twice :: "('a \<Rightarrow> 'a) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "apply_twice f x = f (f x)"

fun apply_once :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "apply_once f x = f x"

fun compose_fn :: "('b \<Rightarrow> 'c) \<Rightarrow> ('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'c" where
  "compose_fn f g x = f (g x)"

fun apply_binary :: "('a \<Rightarrow> 'b \<Rightarrow> 'c) \<Rightarrow> 'a \<Rightarrow> 'b \<Rightarrow> 'c" where
  "apply_binary f x y = f x y"

fun choose_apply :: "bool \<Rightarrow> ('a \<Rightarrow> 'a) \<Rightarrow> ('a \<Rightarrow> 'a) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "choose_apply b f g x = (if b then f x else g x)"

export_code
  apply_twice_int apply_twice apply_once compose_fn apply_binary choose_apply
  in Rust

end
