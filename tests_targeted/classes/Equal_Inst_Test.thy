theory Equal_Inst_Test
  imports Main "Rust.Rust_Setup"
begin

(* A monomorphic datatype with derived equality, used through `fun_upd` (which
   carries a polymorphic `A : equal` bound) and through `=` directly.

   Regression for two coupled dispatch bugs:
   * the equality instance of a concrete type must be reconstructed into an
     `impl Equal for Color` block (it has no sort-context, so the old
     vs-only reconstruction skipped it, leaving `Color: Equal` unsatisfied);
   * the polymorphic helpers `eq`/`fun_upd` are free `fn`s carrying a dict and
     must be called WITHOUT a `Tyco::` prefix, while the class method `equal`
     dispatches as `Color::equal` / `A::equal`. *)

datatype color = Red | Green | Blue

definition set_color :: "(color \<Rightarrow> nat) \<Rightarrow> color \<Rightarrow> nat \<Rightarrow> (color \<Rightarrow> nat)" where
  "set_color f c n = f(c := n)"

definition eq_color :: "color \<Rightarrow> color \<Rightarrow> bool" where
  "eq_color a b = (a = b)"

export_code set_color eq_color in Rust

end
