theory Itself_Dispatch_Test
  imports Main "Rust.Rust_Setup"
begin

(* A class method taking ''a itself'' — the shape of Word_Lib's
   `len_of :: 'a itself => nat`, which the bpf `step` export relies on.
   Exercises:

   * the trait method signature must render the class's own type variable as
     `Self`, even nested: `fn bwidth_of(x0: Itself<Self>)`, not `Itself<A>`
     (A would be unbound in the trait);
   * such a method needs `where Self: Sized` — in a trait `Self` is implicitly
     `?Sized` and `Itself<Self>` is a by-value parameter (E0277 otherwise);
   * a call `bwidth_of TYPE('a)` dispatches on the type carried by the
     dictionary, not on the argument type `'a itself`: generically it is
     `A::bwidth_of(Itself::Type(..))` (gen_bw), and on a concrete instance it is
     `Base::bwidth_of(..)` (base_bw).

   (Dispatch on a *parameterised* concrete type, e.g. `bwidth_of TYPE('a cell)`,
   would need turbofish/qualified-Self to infer the type param and is NOT
   exercised here — the bpf `step` export never does it.) *)

class bwidth =
  fixes bwidth_of :: "'a itself \<Rightarrow> nat"

datatype base = Base

instantiation base :: bwidth
begin
definition "bwidth_of (x::base itself) = 0"
instance ..
end

definition base_bw :: nat where
  "base_bw = bwidth_of TYPE(base)"

definition gen_bw :: "'a::bwidth itself \<Rightarrow> nat" where
  "gen_bw (x::'a itself) = bwidth_of TYPE('a)"

export_code base_bw gen_bw in Rust

end
