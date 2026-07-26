theory AlgebraicStructure_Test
imports Main "HOL-Library.Monad_Syntax" "Rust.Rust_Base_Setup"
begin

(* Cleaned for the Rust export suite. The original theory did not elaborate
   under Isabelle 2025:
   * `functor map_F`/`map_t` and `isort`'s termination are proved with `sorry`,
     which needs `quick_and_dirty` mode;
   * `thm AlgebraicStructure.list.comp` references a fact whose name changed.
   These, together with the `real`/state/IO-monad and `set`-monad material
   (`vlen`, `list3`, `set*`, the `State_Monad` stack, the I/O streams), are
   neither exported nor depended on by an exported constant, so they are
   dropped. The monoid instances are kept (they back the exportable arithmetic
   but are not themselves exported). The option/list-monad helpers, `swap`, and
   the list/option/tree functor maps below export and compile cleanly. *)

section \<open>monoid\<close>

class monoid =
  fixes mult :: "'a \<Rightarrow> 'a \<Rightarrow> 'a" (infixl "\<otimes>" 70)
  fixes neutral :: 'a ("\<one>")
  assumes assoc : "(x \<otimes> y) \<otimes> z = x \<otimes> (y \<otimes> z)"
     and  neutr : "x \<otimes> \<one> = x"
     and  neutl : "\<one> \<otimes> x = x"

instantiation int :: monoid
begin
definition mult_int_def : "x \<otimes> y = (x :: int) + y"
definition neutral_int_def : "\<one> = (0::int)"

instance
  apply standard using neutral_int_def mult_int_def by auto
end

instantiation nat :: monoid
begin
definition mult_nat_def : "x \<otimes> y = (x :: nat) + y"
definition neutral_nat_def : "\<one> = (0::nat)"

instance
  apply standard using neutral_nat_def mult_nat_def by auto
end

instantiation list :: (type) monoid
begin
definition mult_list_def : "(x :: 'a list) \<otimes> y = x @ y"
definition neutral_list_def : "\<one> = []"

instance
  apply standard using neutral_list_def mult_list_def by auto

end


section \<open>monad\<close>

subsection \<open>motivation example\<close>

definition eval :: int
where "eval \<equiv> let x = 1;
                  y = x + 5;
                  z = x + y;
                  z = z * 2
               in z div 2"

subsection \<open>option monad\<close>

definition returno :: "'a \<Rightarrow> 'a option" where
"returno a = Some a"

definition add :: "int option \<Rightarrow> int option \<Rightarrow> int option"
  where "add x y \<equiv> do {
                     mx \<leftarrow> x;
                     my \<leftarrow> y;
                     returno (mx + my)
                   }"

definition adds :: "int option \<Rightarrow> int option"
where "adds x \<equiv> do {
                  a \<leftarrow> x;
                  b \<leftarrow> add (Some a) (Some 1);
                  c \<leftarrow> add (Some b) (Some 2);
                  d \<leftarrow> add (Some c) (Some 3);
                  returno d
                }"

definition safe_div :: "int option \<Rightarrow> int option \<Rightarrow> int option"
  where "safe_div x y \<equiv>
    do {
      mx \<leftarrow> x;
      my \<leftarrow> y;
      if my \<noteq> 0 then returno (mx div my) else None
    }"

definition comps :: "int option \<Rightarrow> int option"
  where "comps x \<equiv>
    do {
       a \<leftarrow> add x (Some (-3));
       b \<leftarrow> safe_div (Some 6) (Some a);
       c \<leftarrow> add (Some b) (Some (-6));
       d \<leftarrow> safe_div (Some 15) (Some c);
       returno d
     }"

subsection \<open>list monad\<close>

context begin

definition returnl :: "'a \<Rightarrow> 'a list"
where "returnl a \<equiv> [a]"

definition "sqr_even l \<equiv>
  do {
    x \<leftarrow> l;
    if x mod 2 = 0 then
      returnl (x * x)
    else returnl x
  }"

definition "list_double l \<equiv>
  do {
    x \<leftarrow> l;
    [x,2*x]
  }"

definition "prod1 xs ys \<equiv>
  do {
    x \<leftarrow> xs;
    y \<leftarrow> ys;
    returnl (x, y)
  }"

definition "prod2 xs ys \<equiv> concat (map (\<lambda>x. concat (map (\<lambda>y. [(x,y)]) ys)) xs)"

definition list2 :: "string list \<Rightarrow> (nat \<times> string) list"
  where "list2 ss \<equiv> do {
                      x \<leftarrow> ss;
                      let y = x@''#'';
                      let z = y@''@'';
                      returnl (length x,z@z)
                    }"

end


section \<open>misc\<close>

definition swap :: "'a list \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> 'a list"
where "swap l i j \<equiv> (let temp = l!i in (l[i := l!j])[j := temp])"


section \<open>functor\<close>

primrec maplist2 :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a list \<Rightarrow> 'b list"
  where "maplist2 f [] = []" |
        "maplist2 f (x # xs) = f x # maplist2 f xs"

functor maplist2
proof
  fix f g x
  show "(maplist2 f \<circ> maplist2 g) x = maplist2 (f \<circ> g) x"
    apply(induct x)
      using maplist2.simps by auto
next
  {
    fix x
    have "(maplist2 id) x = id x"
      apply(induct x)
        using maplist2.simps by auto
  }
  then show "maplist2 id = id" by blast
qed

primrec mapsome :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a option \<Rightarrow> 'b option"
  where "mapsome f None = None" |
        "mapsome f (Some a) = Some (f a)"

functor mapsome
proof
  fix f g x
  show "(mapsome f \<circ> mapsome g) x = mapsome (f \<circ> g) x"
    apply(induct x)
      using mapsome.simps by auto
next
  show "mapsome id = id"
    using mapsome.simps
    by (metis eq_id_iff not_None_eq)
qed

datatype 'a tree = Leaf 'a | Node "'a tree" "'a tree"

primrec maptree :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a tree \<Rightarrow> 'b tree"
  where "maptree f (Leaf a) = Leaf (f a)" |
        "maptree f (Node l r) = Node (maptree f l) (maptree f r)"

lemma lmmt1: "(maptree f \<circ> maptree g) x = (maptree (f \<circ> g)) x"
  apply(induct x)
  using maplist2.simps by auto

lemma lmmt2: "(maptree id) x = id x"
  apply(induct x)
  using maptree.simps by auto

functor maptree
proof
  fix f::"'b \<Rightarrow> 'c"
  fix g::"'a \<Rightarrow> 'b"
  fix x::"'a tree"
  show "(maptree f \<circ> maptree g) x = maptree (f \<circ> g) x"
    using lmmt1 by simp
next
  show "maptree id = id"
    using lmmt2 by blast
qed


export_code eval returno add adds safe_div comps returnl sqr_even list_double prod1 prod2 list2 swap maplist2 mapsome maptree in Rust

end
