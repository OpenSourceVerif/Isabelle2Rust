theory Abstractions_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Basic lambda terms. *)
definition id_abs :: "'a \<Rightarrow> 'a" where
  "id_abs \<equiv> (\<lambda>x. x)"

definition inc_abs :: "int \<Rightarrow> int" where
  "inc_abs \<equiv> (\<lambda>x. x + 1)"

definition apply_abs where
  "apply_abs = (\<lambda>x::int. x + 1) 10"

(* Curried abstractions and captured variables. *)
definition add_n :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "add_n n \<equiv> (\<lambda>x. x + n)"

definition add_n2 :: "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

definition const_fun :: "'a \<Rightarrow> ('b \<Rightarrow> 'a)" where
  "const_fun x = (\<lambda>_. x)"

definition local_abs :: "int \<Rightarrow> int" where
  "local_abs n =
    (let f = ((\<lambda>x::int. x + n) :: int \<Rightarrow> int)
     in f 1)"

definition capture_1 where
  "capture_1 =
    (let y::int = 1 in
     let f = (\<lambda>x. x + y) in
     let j = (\<lambda>x. x + y) in
     let z::int = y in
       f 2)"

definition capture_2 :: "int" where
  "capture_2 =
    (let a::int = 3 in
     let b::int = 4 in
     let f = (\<lambda>x::int. x + a + b) in
     let g = (\<lambda>x::int. a * x + b) in
     let s::int = a + b in
       (f s) + (g s))"

(* Escaping abstractions and typed positions. *)
definition make_pair :: "int \<Rightarrow> (int \<Rightarrow> int) \<times> int" where
  "make_pair y = ((\<lambda>x. x + y), y)"

definition capture_pair :: "'a \<Rightarrow> ('b \<Rightarrow> 'a) \<times> 'a" where
  "capture_pair x = ((\<lambda>_. x), x)"

datatype reg = Reg "nat \<Rightarrow> nat"

definition make_reg :: "nat \<Rightarrow> reg" where
  "make_reg n = Reg (\<lambda>x. x + n)"

fun apply_reg :: "reg \<Rightarrow> nat \<Rightarrow> nat" where
  "apply_reg (Reg f) x = f x"

definition choose_fun :: "nat \<Rightarrow> bool \<Rightarrow> (nat \<Rightarrow> nat)" where
  "choose_fun n b = (if b then (\<lambda>x. x + n) else (\<lambda>x. x * n))"

datatype 'a chooser = Chooser "bool \<Rightarrow> 'a \<Rightarrow> 'a"

definition make_chooser :: "'a \<Rightarrow> 'a chooser" where
  "make_chooser d = Chooser (\<lambda>b x. if b then x else d)"

fun run_chooser :: "'a chooser \<Rightarrow> bool \<Rightarrow> 'a \<Rightarrow> 'a" where
  "run_chooser (Chooser f) b x = f b x"

export_code
  id_abs inc_abs apply_abs add_n add_n2 const_fun local_abs capture_1 capture_2
  make_pair capture_pair make_reg apply_reg choose_fun make_chooser run_chooser
  in Rust

end
