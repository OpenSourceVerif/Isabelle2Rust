theory InfixPrecedence_Test
  imports Main "Rust.Rust_Setup"
begin

(* Nested infix terms must keep the intended precedence after printing. *)

datatype iexpr =
    Lit integer
  | Add iexpr iexpr

fun eval :: "iexpr \<Rightarrow> integer" where
  "eval (Lit n) = n"
| "eval (Add l r) = eval l + eval r"

fun mix :: "integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer" where
  "mix a b c d e = (a + b) * c - d * e"

fun build :: "integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> integer \<Rightarrow> iexpr" where
  "build a b c d = Add (Lit (a + b)) (Lit (c * d))"

export_code
  eval mix build
  in Rust

end
