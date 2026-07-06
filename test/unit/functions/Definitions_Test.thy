theory Definitions_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Fun_Upd_Test"


class my_cls =
  fixes my_op :: "'a \<Rightarrow> 'a"

definition apply_first :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "apply_first g x = g (my_op x)"

definition test_call :: "(('a::my_cls) \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b" where
  "test_call f x = apply_first f x"

subsection "From Func_Add_Int3_Test"


definition add3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add3 x y z = x + y + z"

subsection "From Func_Add_Int_Test"



fun add_int :: "int \<Rightarrow> int \<Rightarrow> int" where
  "add_int x y = x + y"
declare [[code_preproc_trace only: add_int]]
print_codeproc

subsection "From Func_Add_Nat_Test"



fun add_nat :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "add_nat x y = x + y"

subsection "From Func_Max_Case_Test"


fun max2:: "int \<Rightarrow> int \<Rightarrow> int" where
"max2 a b = (
   case a > b of
     True \<Rightarrow> a |
     False \<Rightarrow> b )
"

subsection "From Func_Max_If_Test"


fun max:: "int \<Rightarrow> int \<Rightarrow> int" where
" max a b = (if a > b then a else b) 
"

subsection "From Infix_Prec_Test"


(* Regression test for the D.1 term-layer de-stringification.

   The term printer used to flatten each application via Pretty.string_of and
   glue the Tyco:: prefix, the Box wrapper and the clone call on as raw strings.
   That funnel is now composed with Pretty.block. This test drives every path
   the rewrite touched, so any malformed token adjacency becomes a Rust compile
   error:

     - a recursive datatype, so constructor arguments are Box-wrapped and matched
       with box patterns;
     - registered infix operators (plus, times, minus) nested so that precedence
       parentheses are required: under times, a sum must be parenthesised;
     - infix expressions that are themselves constructor arguments, so the Tyco::
       prefix is composed around a bracketed sub-term;
     - clone placement on variables.

   Variables are kept single-use in the bare infix positions: registered infix
   operators print their operands without a clone, so reusing a (non-Copy) BigInt
   variable there would move it twice. That is the separate H5 over/under-clone
   issue, not part of D.1, so this test steers around it. *)

datatype iexpr = Lit integer | Add iexpr iexpr

fun eval :: "iexpr \<Rightarrow> integer" where
  "eval (Lit n) = n"
| "eval (Add l r) = eval l + eval r"

(* Nested infix precedence with distinct single-use variables.
   Expected Rust: (a + b) * c - d * e, i.e. a + b parenthesised under *. *)
fun mix :: "integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer" where
  "mix a b c d e = (a + b) * c - d * e"

(* Infix expressions as constructor arguments over a Box-wrapped recursive type. *)
fun build :: "integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> iexpr" where
  "build a b c d = Add (Lit (a + b)) (Lit (c * d))"

subsection "From Module_Collision_Test"


(* Regression target for H4 (D.4): two constants forced into DIFFERENT modules
   with the SAME base name, both referenced from a third module.

   The old modify_deresolver truncates every resolved name to its last segment
   and compensates with `use crate::<mod>::*;` glob imports. With two modules
   each exporting a `dup`, the importer's flat namespace gets two `dup` globs ->
   ambiguous reference (rustc E0659). A qualified deresolve (crate::ModA::dup vs
   crate::ModB::dup) removes the ambiguity. *)

definition alpha :: nat where "alpha = 0"
definition beta :: nat where "beta = 0"

definition use_both :: nat where "use_both = alpha + beta"

code_identifier
  constant alpha \<rightharpoonup> (Rust) "ModA.dup"
| constant beta  \<rightharpoonup> (Rust) "ModB.dup"

 (* module_name Use_both*)
 (*export_code use_both in Go*)

subsection "From Mut_Ref_Test"


datatype nat_list =
    Nil
  | Cons nat nat_list

fun sum_acc :: "nat_list \<Rightarrow> nat \<Rightarrow> nat" where
  "sum_acc Nil acc = acc"
| "sum_acc (Cons x xs) acc = sum_acc xs (acc + x)"

definition sum :: "nat_list \<Rightarrow> nat" where
  "sum xs = sum_acc xs 0"

subsection "From Return_Poly_Test"


(* Return-type polymorphism: a class method / function whose type variable occurs
   ONLY in the return type, not in any argument, so the call site cannot infer it.

   conv :: nat => 'a::pseudo_num returns 'a but takes only a nat. When the
   recursive result is shared through a let (the shape HOL's numeral :: num =>
   'a::numeral compiles to, which the bpf step export uses), Rust cannot pick the
   type argument of the let-bound call:

       let m = conv(n.clone());           // conv::<?> -- ? undetermined
       A::pn_add(A::pn_add(m, m), A::pn_one())

   -> error[E0282]: type annotations needed.

   The same root cause shows up as E0283 'type annotations needed for Word<_>' on
   of_int :: int => 'a::len word results in step, where the word WIDTH is the
   return-only-polymorphic parameter.

   Fix: at a call whose result type variable is not fixed by its argument
   types, emit turbofish conv::<A>(..) / of_int::<Width>(..) reconstructed from
   the concrete types carried in the call's IConst record (dom/range). *)

class pseudo_num =
  fixes pn_zero :: "'a"
    and pn_one  :: "'a"
    and pn_add  :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun conv :: "nat \<Rightarrow> 'a::pseudo_num" where
  "conv 0 = pn_zero"
| "conv (Suc n) = (let m = conv n in pn_add (pn_add m m) pn_one)"

export_code
  test_call add3 add_int add_nat max2 max eval mix build use_both sum conv
  in Rust

end
