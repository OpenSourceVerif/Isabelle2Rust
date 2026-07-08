theory PatternBindings_Test
  imports Main "Rust.Rust_Setup"
begin

(* Irrefutable patterns exercise the direct-binding case of pattern matching. *)
datatype 'a single = Single 'a

definition case_id :: "'a \<Rightarrow> 'a" where
  "case_id x = (case x of y \<Rightarrow> y)"

definition unbox_single :: "'a single \<Rightarrow> 'a" where
  "unbox_single x = (case x of Single y \<Rightarrow> y)"

definition let_pair1 :: "'a \<times> 'b \<Rightarrow> 'a" where
  "let_pair1 p = (let (x, _) = p in x)"

definition let_pair2 :: "'a \<times> 'b \<Rightarrow> 'b \<times> 'a" where
  "let_pair2 p = (let (x, y) = p in (y, x))"

(* Local lets are kept here because they introduce term-local bindings. *)
definition let_1 :: "nat \<Rightarrow> nat" where
  "let_1 n =
    (let x = n + 1
     in x * 2)"

fun let_case :: "int \<Rightarrow> int" where
  "let_case x = (let z = 1 in case z of y \<Rightarrow> y + z)"

fun let_chain :: "int \<Rightarrow> int" where
  "let_chain x =
    (let y = 1 in
     let z = y + 1 in
     let y = z + 1 in
       z)"

definition let_shadow :: "'a \<Rightarrow> 'a \<times> 'a" where
  "let_shadow x =
     (let y = x;
          x = y
      in (x, y))"

export_code
  case_id unbox_single let_pair1 let_pair2 let_1 let_case let_chain let_shadow
  in Rust

end
