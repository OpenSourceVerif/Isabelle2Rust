theory Infix_Prec_Test
  imports Main "Rust.Rust_BigInt_Setup"
begin

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

export_code eval mix build in Rust

end
