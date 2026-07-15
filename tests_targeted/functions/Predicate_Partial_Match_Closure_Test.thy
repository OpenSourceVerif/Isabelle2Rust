theory Predicate_Partial_Match_Closure_Test
  imports Main "Rust.Rust_Setup"
begin

(* Predicate compilation represents each rule branch as a function returning a
   predicate sequence.  Constructor-specific branches are partial: their
   generated fallback is a closure whose body only raises the backend's panic
   stub.  When that closure is coerced to Rc<dyn Fn(..) -> Predicate.pred unit>,
   Rust must still see the predicate result type explicitly; otherwise it fixes
   the closure's Output to the never type and rejects the trait-object coercion.
   The three rules below exercise both empty and constructor list patterns in
   the generated predicate functions. *)
inductive partial_sublist :: "'a list \<Rightarrow> 'a list \<Rightarrow> bool"
where
  empty: "partial_sublist [] xs"
| drop: "partial_sublist ys xs \<Longrightarrow> partial_sublist ys (x # xs)"
| take: "partial_sublist ys xs \<Longrightarrow> partial_sublist (x # ys) (x # xs)"

code_pred partial_sublist .

definition check_partial_sublist :: "nat list \<Rightarrow> nat list \<Rightarrow> bool"
where
  "check_partial_sublist xs ys \<longleftrightarrow> partial_sublist xs ys"

export_code check_partial_sublist in Rust

end
