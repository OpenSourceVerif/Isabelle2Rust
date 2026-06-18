theory Nat_BigInt_Test
  imports Main "Rust.Rust_BigInt_Nat_Setup"
begin

(* Exercise the nat/int -> BigInt mapping from Rust_BigInt_Nat_Setup, which
   imports Rust_BigInt_Int_Setup: neither nat nor int may be emitted as a unary
   `enum`, but mapped to BigInt with
   arithmetic/comparisons printed as native BigInt ops. Includes int equality /
   ordering (which reconstruct an `impl Equal/Ord for int` whose header must print
   `int` via tyco_syntax, not deresolve), mirroring the bpf_generator usage. *)

fun count_down :: "nat \<Rightarrow> nat" where
  "count_down 0 = 0"
| "count_down (Suc n) = Suc (count_down n)"

definition add_nats :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "add_nats a b = a + b * 2"

definition int_eq :: "int \<Rightarrow> int \<Rightarrow> bool" where
  "int_eq a b = (a = b)"

definition int_lt :: "int \<Rightarrow> int \<Rightarrow> bool" where
  "int_lt a b = (a < b)"

definition int_sum :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_sum a b = a + b - 1"

definition pick :: "bool \<Rightarrow> 'a::zero_neq_one" where
  "pick b = of_bool b"

definition pick_int :: "bool \<Rightarrow> int" where
  "pick_int b = pick b"

export_code count_down add_nats int_eq int_lt int_sum pick_int in Rust

end
