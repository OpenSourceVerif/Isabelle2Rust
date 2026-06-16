theory Return_Poly_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code conv in Rust

end
