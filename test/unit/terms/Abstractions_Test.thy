theory Abstractions_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Abs_Addn_Test"



definition add_n :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "add_n n \<equiv> (\<lambda>x. x + n)" 

subsection "From Abs_Capture_Multi_Test"


(* Regression test for closure capture handling.
   Before the fix, a `move` closure consumed every captured outer variable,
   making subsequent closures or uses fail to compile in Rust.
   The fix pre-copies each captured variable into a fresh `_cap` binding
   and rewrites free occurrences inside the closure body accordingly.
   This case exercises multiple captures shared by multiple closures, with
   the captured variables still used afterwards. *)

definition multi_caps :: "int" where
"multi_caps = (let a::int = 3 in
                let b::int = 4 in
                let f = (\<lambda>x::int. x + a + b) in
                let g = (\<lambda>x::int. a * x + b) in
                let s::int = a + b in
                (f s) + (g s))"

subsection "From Abs_Capture_Test"



definition closure_1 where
" closure_1 = (let y::int = 1 in
                let f = (\<lambda>x. x + y) in
                
                let j = (\<lambda>x. x + y) in
                   let z :: int = y in
                  f 2)
"



definition make_pair :: "int \<Rightarrow> (int \<Rightarrow> int) \<times> int" where
"make_pair y = ((\<lambda>x. x + y), y)"

subsection "From Abs_Inc_Test"


definition inc :: "int \<Rightarrow> int" where
  "inc \<equiv> (\<lambda>x. x + 1)"

subsection "From Abs_Nested_Test"


definition add_n_2 ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
"add_n_2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

subsection "From Abs_No_Capture_Test"



definition closure_2 where
"closure_2 =(\<lambda>x::int. x + 1) 10
"

subsection "From Abs_Poly_Test"



definition id :: "'a \<Rightarrow> 'a" where
  "id \<equiv> (\<lambda>x. x)"

subsection "From Closure_Boxing_Test"


(* HOL treats functions as ordinary first-class values; Rust's `impl Fn` does
   not cover all the same uses. Two operations require a cloneable boxed closure
   `Rc<dyn Fn(..)>` to translate faithfully:

   OP1 -- store a function in a datatype FIELD. `impl Trait` is illegal in field
          types (E0562): each closure is a distinct anonymous type, so the field
          can only be a `dyn Fn` behind a pointer.
   OP2 -- have one return position hold one of several DIFFERENT *capturing*
          closures (here, two branches). `impl Fn` is a single concrete type;
          two distinct capturing closures do not unify (E0308: "no two closures
          ... have the same type"). NB non-capturing closures coerce to `fn` and
          would unify, so OP2 must capture to bite.

   Combined with the derived `Clone` (`#[derive(Clone)]`) and the `+ Clone`
   bounds the backend emits, the boxed form must be `Rc<dyn Fn>` rather than
   `Box<dyn Fn>` -- the latter is not `Clone` (E0277).

   This is exactly the shape of bpf `step`'s `BpfState`, which stores the
   register file (`BpfIreg => Word`) and memory (`Word => Word option`) as fields
   and rebuilds them with capturing closures (fun_upd, memory update).

   Now GREEN: the backend maps HOL function types to Rc<dyn Fn(..)> and wraps
   lambda values in Rc::new, so both OP1 and OP2 translate faithfully. *)

(* OP1: a function stored in a datatype field. *)
datatype reg = Reg "nat \<Rightarrow> nat"

definition mk_reg :: "nat \<Rightarrow> reg" where
  "mk_reg n = Reg (\<lambda>x. x + n)"

fun app_reg :: "reg \<Rightarrow> nat \<Rightarrow> nat" where
  "app_reg (Reg f) x = f x"

(* OP2: two different capturing closures in one return position. *)
definition pick :: "nat \<Rightarrow> bool \<Rightarrow> (nat \<Rightarrow> nat)" where
  "pick n b = (if b then (\<lambda>x. x + n) else (\<lambda>x. x * n))"

export_code
  add_n multi_caps make_pair inc add_n_2 closure_2 id mk_reg app_reg pick
  in Rust

end
