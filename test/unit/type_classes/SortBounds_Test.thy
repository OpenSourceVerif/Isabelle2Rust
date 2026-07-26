theory SortBounds_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Source sorts with several classes become multiple Rust trait bounds. *)

class seed =
  fixes seed :: "'a"

class tick =
  fixes tick :: "'a \<Rightarrow> 'a"

fun step_or_seed :: "bool \<Rightarrow> ('a::{seed,tick}) \<Rightarrow> 'a" where
  "step_or_seed True x = tick x"
| "step_or_seed False _ = seed"

definition seed_pair :: "('a::{seed,tick}) \<Rightarrow> 'a \<times> 'a" where
  "seed_pair x = (seed, tick x)"

export_code
  step_or_seed seed_pair
  in Rust

end
