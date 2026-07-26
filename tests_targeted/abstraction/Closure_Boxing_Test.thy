theory Closure_Boxing_Test
  imports Main "Rust.Rust_Base_Setup"
begin

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

export_code mk_reg app_reg pick in Rust

end
