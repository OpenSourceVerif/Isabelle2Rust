theory Class_Multi_Method_Test
  imports Main "Rust.Rust_Setup"
begin

(* Regression test: a type class with TWO methods, instantiated for a
   POLYMORPHIC type.  Isabelle eliminates the Classinst node and emits two
   specialized projection functions
     twoop_Wrap_inst.op1_Wrap  and  twoop_Wrap_inst.op2_Wrap
   that share the same `twoop_Wrap_inst` segment.  The old per-method
   heuristic wrapped each one in its own `impl Twoop for Wrap { .. }` block,
   producing two conflicting impls (Rust E0119 + E0046).  The fix groups both
   methods into a single impl block. *)

class twoop =
  fixes op1 :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "<+>" 65)
    and op2 :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "<*>" 65)

datatype 'a Wrap = Wrap 'a        

instantiation Wrap :: (twoop) twoop
begin

fun op1_Wrap :: "('a::twoop) Wrap \<Rightarrow> 'a Wrap \<Rightarrow> 'a Wrap" where
  "Wrap x <+> Wrap y = Wrap (x <+> y)"

fun op2_Wrap :: "('a::twoop) Wrap \<Rightarrow> 'a Wrap \<Rightarrow> 'a Wrap" where
  "Wrap x <*> Wrap y = Wrap (x <*> y)"

instance ..
end

fun combine :: "('a::twoop) Wrap \<Rightarrow> 'a Wrap \<Rightarrow> 'a Wrap \<Rightarrow> 'a Wrap" where
  "combine a b c = (a <+> b) <*> c"

export_code combine in Rust

end
