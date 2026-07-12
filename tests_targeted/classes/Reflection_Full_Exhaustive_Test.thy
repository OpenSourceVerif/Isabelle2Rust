theory Reflection_Full_Exhaustive_Test
  imports "HOL.Quickcheck_Exhaustive" "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: String.rs `FullExhaustive for Char`,
   representative of Records.rs, Code_Evaluation.rs, Enum.rs and the generated
   Quickcheck instances -- E0277 plus E0631).

   A generated `full_exhaustive` method threads values together with thunks of
   type `unit \<Rightarrow> term`.  To enumerate a function-valued intermediate,
   the Rust blanket impl requires both its argument to implement `Equal` and its
   result to implement `FullExhaustive`.  The reconstructed Char method applies
   that impl to callbacks containing `term`.  In the broad graph this reaches
   repeated `Term: Equal` and `Term: FullExhaustive` failures; in this reduced
   export rustc first exposes missing upstream `bool: Typerep` and function
   `FullExhaustive` impls.  Both are facets of the same unsatisfied generated
   reflection-instance graph, and closure-signature mismatches follow in the
   nested callbacks.

   This is Isabelle testing/reflection infrastructure rather than an executable
   user algorithm.  The eventual Phase-B resolution may explicitly exclude it,
   but until then this test records its compact Char representative. *)

definition dispatch_full_exhaustive ::
  "(('a::full_exhaustive \<times> (unit \<Rightarrow> term)) \<Rightarrow>
    (bool \<times> term list) option) \<Rightarrow> natural \<Rightarrow> (bool \<times> term list) option" where
  "dispatch_full_exhaustive f i =
    Quickcheck_Exhaustive.full_exhaustive_class.full_exhaustive f i"

definition char_full_exhaustive ::
  "((char \<times> (unit \<Rightarrow> term)) \<Rightarrow>
    (bool \<times> term list) option) \<Rightarrow> natural \<Rightarrow> (bool \<times> term list) option" where
  "char_full_exhaustive = dispatch_full_exhaustive"

export_code String.full_exhaustive_char_inst.full_exhaustive_char
  dispatch_full_exhaustive char_full_exhaustive in Rust

end
