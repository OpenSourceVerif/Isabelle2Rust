theory Traits_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Class_Multi_Method_Test"


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

subsection "From Class_No_Ins2_Test"


class plus =
  fixes plus :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

fun add_pair :: "('a::plus) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "add_pair x y = plus x y"

subsection "From Class_Superclass_Test"


class add1 =
  fixes add1 :: "'a \<Rightarrow> 'a"

class add2 =
  fixes add2 :: "'a \<Rightarrow> 'a"

class add1_add2 = add1 + add2

fun add12 :: "('a::add1_add2) \<Rightarrow> 'a" where
  "add12 x = add2 (add1 x)"

subsection "From Equal_Inst_Test"


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

subsection "From Equal_Pair_Test"


(* REGRESSION — `HOL.equal` on a tuple / `prod` (now FIXED, exports + compiles).

   Trigger: comparing a pair with `=` forces the code generator to emit the
   `equal :: prod ⇒ prod ⇒ bool` instance (`equal_prod`). `prod`/`Pair` are
   registered in `Rust_Setup.thy` only as the mixfix templates
   `type_constructor prod ⇀ "( _ , _ )"` and `constant Pair ⇀ "( _ , _ )"`
   (Rust has no nominal Pair constructor), so the instance must be reconstructed
   as `impl<A: Equal, B: Equal> Equal for (A, B)`.

   The fix is in `code_rust.ML`:
   * `canon_tyco` now feeds the tuple mixfix template placeholder args matching
     its arity (it formerly passed `[]`, crashing `printer_of_mixfix`);
   * an instance-method call whose receiver type is mixfix-mapped (a tuple) is
     dispatched through Rust's fully qualified form
     `<(A, B) as Equal>::equal(..)` instead of the inexpressible `Tyco::equal`.

   The reconstructed `impl Equal for (A, B)` recurses through the element
   `Equal` bounds, exactly mirroring the native structural tuple equality the
   OCaml/Haskell/SML backends rely on.

   Same root cause behind the fpp `AVL_Set_Code_Test` and `Set_Relation_Test`
   (`(string × string) set`) failures; see also `types/Set_Pair_Test.thy`. *)

definition eq_pair :: "nat \<times> nat \<Rightarrow> bool" where
  "eq_pair p = (p = (0, 0))"

subsection "From Int_Zero_Inst_Test"


(* `0::int` is registered as a code_datatype constructor for int
   (`code_datatype "0::int" Pos Neg` in HOL/Int.thy), so Isabelle generates NO
   `zero_int_inst.zero_int` function -- zero is the constructor `Int::ZeroInta`.
   `one::int`, by contrast, has a real code equation (`1 = Pos Num.One`).

   A polymorphic `zero_neq_one` consumer instantiated at int therefore needs a
   reconstructed `impl Zero for Int` whose `zero()` returns the constructor, not
   a `panic!` stub. `of_bool :: bool => 'a::zero_neq_one` is exactly such a
   consumer; keeping it behind a polymorphic helper forces the trait-method
   dispatch `Int::zero()` / `Int::one()` rather than inlining. *)

definition pick :: "bool \<Rightarrow> 'a::zero_neq_one" where
  "pick b = of_bool b"

definition pick_int :: "bool \<Rightarrow> int" where
  "pick_int b = pick b"

subsection "From Itself_Dispatch_Test"


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

subsection "From Trait_Cross_Module_Test"


(* Regression test for R1 (D.4 finish): cross-module trait-method dispatch with
   globs removed. The trait `sg` and its method are forced into a separate Rust
   module `ClsMod`; the polymorphic dispatch `combine x y` (-> A::combine, since
   the receiver is a type variable) lives in the theory module and is reached via
   `use_t`. For `A::combine` / the `impl sg for T` to resolve, `ClsMod`'s trait
   must be in scope. With glob imports removed, this now requires the explicit
   `use crate::ClsMod::Sg;` that R1 emits. *)

class sg = fixes combine :: "'a \<Rightarrow> 'a \<Rightarrow> 'a"

datatype T = A | B

instantiation T :: sg
begin
fun combine_T :: "T \<Rightarrow> T \<Rightarrow> T" where
  "combine_T A y = y"
| "combine_T B y = B"
instance ..
end

(* polymorphic dispatch through the class: receiver is a tyvar -> A::combine *)
fun foldpair :: "('a::sg) \<Rightarrow> 'a \<Rightarrow> 'a" where
  "foldpair x y = combine x y"

definition use_t :: T where "use_t = foldpair A B"

code_identifier
  type_class sg \<rightharpoonup> (Rust) "ClsMod.sg"
| constant combine \<rightharpoonup> (Rust) "ClsMod.combine"

export_code
  combine add_pair add12 set_color eq_color eq_pair pick_int base_bw gen_bw use_t
  in Rust

end
