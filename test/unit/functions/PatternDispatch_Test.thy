theory PatternDispatch_Test
  imports Main "Rust.Rust_Base_Setup"
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

(* A wildcard row following a boxed constructor row must remain reachable.
   Since these Box fields contain only wildcards, stable Rust can preserve the
   original tuple match without staged destructuring. *)
fun boxed_wildcard_fallback :: "token \<Rightarrow> token \<Rightarrow> nat" where
  "boxed_wildcard_fallback (Join _ _) (Push n) = n"
| "boxed_wildcard_fallback t Stop = token_size t"
| "boxed_wildcard_fallback _ _ = 0"

(* Native tuples nested with a boxed list pattern must remain visible to the
   stable match compiler. *)
fun pair_list_sum :: "(nat \<times> nat) list \<Rightarrow> nat" where
  "pair_list_sum ((x, y) # _) = x + y"
| "pair_list_sum [] = 0"

fun nested_pair_list_sum :: "nat \<times> (nat \<times> nat) list \<Rightarrow> nat" where
  "nested_pair_list_sum (z, (x, y) # _) = z + x + y"
| "nested_pair_list_sum (_, []) = 0"

definition nested_pair_list_case :: "nat \<times> (nat \<times> nat) list \<Rightarrow> nat" where
  "nested_pair_list_case input =
    (case input of
       (z, (x, y) # _) \<Rightarrow> z + x + y
     | (_, []) \<Rightarrow> 0)"

export_code
  token_size choose_nat token_score first_some boxed_wildcard_fallback
  pair_list_sum nested_pair_list_sum nested_pair_list_case
  in Rust

end
