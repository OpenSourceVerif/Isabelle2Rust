theory PatternDispatch_Test
  imports Main "Rust.Rust_Setup"
begin

(* Refutable left-hand-side patterns are compiled into match dispatch. *)

datatype token =
    Stop
  | Push nat
  | Join token token

fun token_size :: "token \<Rightarrow> nat" where
  "token_size Stop = 0"
| "token_size (Push _) = 1"
| "token_size (Join l r) = token_size l + token_size r"

fun choose_nat :: "bool \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "choose_nat True x _ = x"
| "choose_nat False _ y = y"

fun token_score :: "token \<Rightarrow> nat \<Rightarrow> nat" where
  "token_score Stop n = n"
| "token_score (Push x) n = x + n"
| "token_score (Join l r) n = token_size l + token_size r + n"

fun first_some :: "'a option \<Rightarrow> 'a \<Rightarrow> 'a" where
  "first_some (Some x) _ = x"
| "first_some None y = y"

export_code
  token_size choose_nat token_score first_some
  in Rust

end
