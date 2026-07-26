theory Mut_Chain_Test
  imports Main "Rust.Rust_Base_Setup"
begin

text \<open>
  Self-contained mut-chain example for the mutability-inference pass.

  The shadowed let-bindings of \<open>x\<close> form a handoff chain that Thingol prints as
  the distinct variables \<open>x\<close>, \<open>xa\<close>, \<open>xb\<close>, \<open>xc\<close> joined by \<open>.clone()\<close> hand-offs.
  The right-hand sides mix a constructor (\<open>S x\<close>) and a helper call (\<open>bump x\<close>),
  showing that the pass is agnostic to what each step computes.  The mut pass
  collapses the chain into a single \<open>let mut x\<close> updated by assignment and drops
  the now-redundant handoff clones.

  Using a custom recursive datatype (rather than \<open>nat\<close>) keeps the export to a
  single module, so it compiles end-to-end without the \<open>nat_of_integer\<close>/
  \<open>Orderings.Ord\<close> machinery that blocks \<^file>\<open>Mut_Nat_Test.thy\<close> at stage1.
\<close>

datatype peano = Z | S peano

fun bump :: "peano \<Rightarrow> peano" where
  "bump n = S (S n)"

definition grow :: "peano \<Rightarrow> peano" where
  "grow n =
    (let x = n in
     let x = S x in
     let x = bump x in
     let x = S x in
     x)"

export_code grow in Rust

end
