theory Dispatch_Test
  imports Main "Rust.Rust_Setup"
begin

(* Overloaded calls are resolved through monomorphic and polymorphic contexts. *)

class semigroup =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "+s" 65)

datatype Nat = Zero | Suc Nat

instantiation Nat :: semigroup
begin

fun plus_Nat :: "Nat \<Rightarrow> Nat \<Rightarrow> Nat" where
  "a +s Zero = a"
| "Zero +s a = a"
| "Suc a +s b = Suc (a +s b)"

instance ..
end

(* Monomorphic instances must still be available through polymorphic dispatch. *)
fun dbl :: "('a::semigroup) \<Rightarrow> 'a" where
  "dbl x = x +s x"

definition use_nat :: Nat where
  "use_nat = dbl (Suc Zero)"

(* Dispatch can be determined by a type carried in an itself argument. *)
class bwidth =
  fixes bwidth_of :: "'a itself \<Rightarrow> nat"

datatype base = Base

instantiation base :: bwidth
begin

definition bwidth_of_base where
  "bwidth_of (x::base itself) = 0"

instance ..
end

definition base_bw :: nat where
  "base_bw = bwidth_of TYPE(base)"

definition gen_bw :: "'a::bwidth itself \<Rightarrow> nat" where
  "gen_bw (x::'a itself) = bwidth_of TYPE('a)"

(* Cross-module trait dispatch needs the trait name in scope. *)
class sg =
  fixes combine :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

datatype T = A | B

instantiation T :: sg
begin

fun combine_T :: "T \<Rightarrow> T \<Rightarrow> T" where
  "combine_T A y = y"
| "combine_T B y = B"

instance ..
end

fun foldpair :: "('a::sg) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "foldpair x y = combine x y"

definition use_t :: T where
  "use_t = foldpair A B"

code_identifier
  type_class sg \<rightharpoonup> (Rust) "ClsMod.sg"
| constant combine \<rightharpoonup> (Rust) "ClsMod.combine"

export_code
  use_nat base_bw gen_bw use_t
  in Rust

end
