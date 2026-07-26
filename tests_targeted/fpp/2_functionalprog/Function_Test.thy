theory Function_Test
  imports HOL.Fun Main "Rust.Rust_Base_Setup"
begin

(* Cleaned for the Rust export suite. The original theory failed to elaborate
   under Isabelle 2025:
   * `sqrt` uses `root` (`HOL-Analysis`/`NthRoot`), not in scope here;
   * `fun5` uses `Fun.swap`, which was moved out of `Fun` (to
     `HOL.Transposition`) in 2025 and is no longer `Fun.swap`.
   Both are dropped (`fun5` is removed from the export list). The remaining
   non-exported proofs, `value` probes and the `the_inv`/`set`/`real` material
   (`func`, `add2`, `suc_inv`, `kvs3`, `kvs4`, …) are neither exported nor
   depended on by an exported constant, so they are dropped too. The executable
   functions below export and compile cleanly. *)

subsection \<open>total and partial function\<close>

definition Pred :: "nat \<rightharpoonup> nat"
  where "Pred n \<equiv> (if n > 0 then Some (n - 1) else None)"

definition minus_nat :: "nat \<Rightarrow> nat \<rightharpoonup> nat"
  where "minus_nat a b \<equiv> (if a \<ge> b then Some (a - b) else None)"

subsection \<open>injective, surjective, bijective\<close>

definition add1 :: "nat \<Rightarrow> nat"
  where "add1 n \<equiv> n + 1"

subsection \<open>function operation\<close>

definition fun1 :: "int \<Rightarrow> int"
  where "fun1 x \<equiv> x + 1"

definition "fun2 x \<equiv> fun1 x * 2"

definition "fun3 \<equiv> (\<lambda>x. (fun1(x := fun1 x * 2)) x)"

definition fun4 :: "int \<Rightarrow> int"
  where "fun4 x \<equiv> x * 2"

definition suc :: "int \<Rightarrow> int"
  where "suc n \<equiv> n + 1"

definition pred :: "int \<Rightarrow> int"
  where "pred n \<equiv> n - 1"

definition suc2 :: "nat \<Rightarrow> nat"
  where "suc2 n \<equiv> n + 2"

definition pred2 :: "nat \<Rightarrow> nat"
  where "pred2 n \<equiv> n - 2"

definition f6 :: "int \<Rightarrow> int"
  where "f6 x \<equiv> (if x < 0 then x + 1 else 10)"

definition f7 :: "int \<Rightarrow> int"
  where "f7 n \<equiv> n + 2"

definition g7 :: "int \<Rightarrow> int"
  where "g7 n \<equiv> n * 2"


subsection \<open>polymorphism\<close>

definition addi :: "int \<Rightarrow> int \<Rightarrow> int"
  where "addi x y \<equiv> x + y"

definition first :: "('a \<times> 'b) \<Rightarrow> 'a"
  where "first p \<equiv> case p of (a,b) \<Rightarrow> a"

definition second :: "('a \<times> 'b) \<Rightarrow> 'b"
  where "second p \<equiv> case p of (a,b) \<Rightarrow> b"

type_synonym 'a array = "'a list"

primrec array_assn :: "'a array \<Rightarrow> nat \<Rightarrow> 'a \<Rightarrow> 'a array" ("_[_] := _")
  where "array_assn [] i v = []" |
        "array_assn (x # xs) i v =
            (case i of 0 \<Rightarrow> v # xs |
                  Suc j \<Rightarrow> x # list_update xs j v)"

definition query :: "'a array \<Rightarrow> nat \<Rightarrow> 'a" ("_[_]")
  where "arr[i] \<equiv> arr ! i"

definition arr1 :: "int array"
  where "arr1 \<equiv> [1,2,3]"
definition "arr2 \<equiv> arr1[1] := 8"

definition arr3 :: "string array"
  where "arr3 \<equiv> [''aaaa'',''bbbb'',''cccc'']"
definition "arr4 \<equiv> arr3[1] := ''eeee''"

type_synonym ('k,'v) kvstore = "'k \<rightharpoonup> 'v"

definition getv :: "('k,'v) kvstore \<Rightarrow> 'k \<Rightarrow> 'v option"
  where "getv m k \<equiv> m k"

definition update :: "('k,'v) kvstore \<Rightarrow> 'k \<Rightarrow> 'v \<Rightarrow> ('k,'v) kvstore" ("_ [_ :\<rightarrow> _]")
  where "update m k v \<equiv> m(k:= Some v)"

datatype 'v valT = I int | S string | L "'v list" | T "'v set"

record info = name :: string
              addr :: string
              val  :: int

type_synonym imap = "(int, info valT) kvstore"

definition kvs1 :: "imap"
  where "kvs1 \<equiv> (\<lambda>i. None)"

definition "kvs2 \<equiv> kvs1[1 :\<rightarrow> (S ''hello'')]"


export_code Pred minus_nat add1 fun1 fun2 fun3 fun4 suc pred suc2 pred2 f6 f7 g7 addi first second array_assn query arr1 arr2 arr3 arr4 getv update kvs1 kvs2 in Rust

end
