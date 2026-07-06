# Test Migration TODO

## 2026-07-03 - `test/fpp/2_functionalprog/BasicDef_Test`

### How it happened

Commands:

```sh
make gen DIR=test/fpp/2_functionalprog Name=BasicDef_Test
make test DIR=test/fpp/2_functionalprog Name=BasicDef_Test
```

Observed result:

- `make gen` succeeds. Stage 1 is generated and `cargo build --locked` passes for
  `test/fpp/2_functionalprog/stage1/BasicDef_Test/export1`.
- `make test` succeeds through Isabelle export and stage2 generation, then fails
  during the stage2 Cargo build for
  `test/fpp/2_functionalprog/stage2/BasicDef_Test`.

### Failure shape

The optimized stage2 crate changes shared functions such as `plus_nat`,
`times_nat`, `nat_of_num`, `plus_int`, `fst`, and `snd` to borrow-taking
signatures, but many call sites in `BasicDef_Test.rs` and generated library
modules still pass owned values.

Representative errors:

```text
src/BasicDef_Test.rs:37:35: expected `&Num`, found `Num`
src/BasicDef_Test.rs:37:14: expected `&Nat`, found `Nat`
src/BasicDef_Test.rs:51:28: expected `&Nat`, found `Nat`
src/Int.rs:92:22: expected `&Num`, found `Num`
src/Product_Type.rs:330:34: expected `&(_, Nat)`, found `(Nat, Nat)`
```

Representative generated code:

```rust
pub fn f(x: Nat) -> Nat {
    plus_nat(times_nat(nat_of_num(Num::Bit0(Box::new(Num::One))), x.clone()),
             one_nat())
}

// borrow-optimized by shared parameters
pub fn plus_nat(x0: &Nat, n: &Nat) -> Nat { ... }
```

### Current diagnosis

This looks like a stage2 borrow-optimization consistency issue, not a stage1
export issue. The optimizer rewrites some callee signatures to borrowed
parameters, but the corresponding inter-module and same-module call sites are
not all rewritten to pass references.

### Suggested fix direction

Check the optimizer pass that applies shared-parameter borrow rewrites. The fix
probably needs to ensure that whenever a function signature is rewritten from
owned parameters to borrowed parameters, every direct call site in the optimized
crate is rewritten consistently, including calls in imported generated modules
such as `Int.rs`, `Arith.rs`, and `Product_Type.rs`.

## 2026-07-03 - Full FPP migration run

### How it happened

Command:

```sh
make test DIR=test/fpp
```

Observed summary:

```text
test summary (test/fpp):
  Exported definitions: Passed: 9 / Failed: 319 / Total: 328
  Theories:             Passed: 7 / Failed: 36 / Total: 43
```

Passed theories:

```text
InsertSort_Test (2)
Cmp_Test (1)
List_Ins_Del_Test (2)
Set_Specs_Test (0)
Big_Step_Test (0)
Com_Test (4)
Small_Step_Test (0)
```

Failed theories:

```text
func_imp_compare_Test (2)
AlgebraicStructure_Test (16)
BasicDef_Test (33)
Classes_Test (6)
FirstExample_Test (1)
Function_Test (27)
Highorder_Func_Test (52)
Listprog_Test (25)
Recursion_Test (26)
Set_Relation_Test (6)
Types_Test (28)
Prog1_Test (2)
Prog2_Test (2)
Prog3_Test (4)
Tutorial_Test (3)
Bubblesort_Test (2)
MergeSort_Test (2)
Quicksort_Test (1)
PriorityQueue_Test (9)
Queue_Test (7)
stack_Test (4)
AVL_Set_Code_Test (8)
AVL_Set_Test (1)
Isin2_Test (1)
Leftist_Heap_Test (11)
Less_False_Test (0)
Priority_Queue_Specs_Test (0)
Sorted_Less_Test (0)
Tree2_Test (1)
Tree_Set_Test (7)
Tree_Test (14)
search_Test (4)
AExp_Test (5)
BExp_Test (4)
Compiler_Test (5)
Star_Test (0)
```

### Failure shape 1: stage2 borrow/call-site mismatch

Most nonzero-export failures reach stage2 generation and then fail in stage2
Cargo compilation. The common shape is Rust `E0308`: optimized callees take
borrowed parameters, while generated call sites still pass owned values.

Representative locations from the full log include:

```text
BasicDef_Test.rs: expected `&Nat`, found `Nat`
Int.rs: expected `&Num`, found `Num`
Set.rs: expected `&A`, found type parameter `A`
Set.rs: expected `&List<A>`, found `List<A>`
```

`Bubblesort_Test` also shows a related borrowed-pattern mismatch:

```text
src/Bubblesort_Test.rs:43:23: expected `Box<List<A>>`, found `List<_>`
```

Current diagnosis: this is the same class as the single `BasicDef_Test` probe.
The optimizer rewrites borrow-taking signatures but does not consistently
rewrite all call sites and pattern sites that depend on those signatures.

Suggested fix direction: audit the stage2 borrow rewrite pass across both
function-call arguments and pattern matches over borrowed data. Re-run this FPP
suite after the optimizer rewrite is made consistent.

### Failure shape 2: Rust export directory is not always `export1`

`Highorder_Func_Test` has earlier non-Rust exports:

```isabelle
export_code fof1 in OCaml
export_code fof1 in Haskell
...
export_code ... in Rust
```

The final Rust export is generated under:

```text
test/fpp/2_functionalprog/stage1/Highorder_Func_Test/export4
```

But the current stage2 pipeline assumes:

```text
test/fpp/2_functionalprog/stage1/Highorder_Func_Test/export1
```

Observed error:

```text
opt failed: failed to resolve test/fpp/2_functionalprog/stage1/Highorder_Func_Test/export1:
No such file or directory
```

Current diagnosis: the Makefile optimizer path is hard-coded to `export1`, which
breaks for theories that contain earlier non-Rust `export_code` commands.

Suggested fix direction: either make the optimizer stage discover the Rust
Cargo export directory under `stage1/<Theory>/export*/Cargo.toml`, or split
non-Rust export checks away from migrated Rust test theories.

### Failure shape 3: support theories with no own Rust export

Some FPP support theories have `0` exported definitions and no generated Rust
crate at the theory's own stage1 path. The bulk test runner still tries to run
stage2 optimization for them.

Observed failures:

```text
Less_False_Test
Priority_Queue_Specs_Test
Sorted_Less_Test
Star_Test
```

Representative error:

```text
opt failed: failed to resolve test/fpp/5_IMP/stage1/Star_Test/export1:
No such file or directory
```

Current diagnosis: these files are support theories rather than exported test
units under the exported-definition counting rule. A bulk run over every
`*_Test.thy` does not match the paper-level counting unit.

Suggested fix direction: decide whether bulk `make test DIR=...` should skip
theories whose last Rust export count is zero, or whether the migrated `test/fpp`
suite should keep support theories in a separate import-only location that is
not treated as a runnable exported test unit.

## 2026-07-03 - First merged targeted suites

### What was migrated

The following low-conflict categories were merged into one suite theory per
category under `test/targeted`:

```text
test/targeted/cases/Case_Suite_Test.thy                8 exported definitions
test/targeted/constructors/Constructor_Suite_Test.thy  11 exported definitions
test/targeted/lets/Let_Suite_Test.thy                  3 exported definitions
test/targeted/lists/List_Suite_Test.thy                2 exported definitions
```

The source-to-suite mapping is recorded in `test/targeted/MIGRATION.md`.

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted
```

Observed summary:

```text
gen summary (test/targeted):
  Exported definitions: Passed: 24 / Failed: 0 / Total: 24
  Theories:             Passed: 4 / Failed: 0 / Total: 4
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted
```

Observed summary:

```text
test summary (test/targeted):
  Exported definitions: Passed: 11 / Failed: 13 / Total: 24
  Theories:             Passed: 1 / Failed: 3 / Total: 4
```

Passed:

```text
Constructor_Suite_Test (11)
```

Failed:

```text
Case_Suite_Test (8)
Let_Suite_Test (3)
List_Suite_Test (2)
```

### Failure shape

The stage2 failures are again Rust `E0308` borrow/call-site mismatches after
optimization. Examples from the merged suites:

```text
Case_Suite_Test: expected borrowed numeric/list arguments after optimization
Let_Suite_Test: plus_num and related Int/Arith calls expect borrowed arguments
List_Suite_Test: size_list expects `&List<_>`, call site passes `List<Nat>`
```

Current diagnosis: the merge itself is valid for stage1. The stage2 failures
match the existing optimizer consistency issue already seen in the FPP run.

Suggested fix direction: after fixing the stage2 borrow rewrite, re-run:

```sh
make gen DIR=test/targeted
make test DIR=test/targeted
```

## 2026-07-03 - Merged abstraction suites

### What was migrated

`tests_targeted/abstraction` was merged into two suite theories to avoid the
duplicate `add_n_2` definition between `Abs_Nested_Test` and
`Unsaturated_Test`:

```text
test/targeted/abstraction/Abstraction_Basic_Suite_Test.thy        10 exported definitions
test/targeted/abstraction/Abstraction_Unsaturated_Suite_Test.thy  1 exported definitions
```

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/abstraction
```

Observed summary:

```text
gen summary (test/targeted/abstraction):
  Exported definitions: Passed: 11 / Failed: 0 / Total: 11
  Theories:             Passed: 2 / Failed: 0 / Total: 2
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/abstraction
```

Observed summary:

```text
test summary (test/targeted/abstraction):
  Exported definitions: Passed: 0 / Failed: 11 / Total: 11
  Theories:             Passed: 0 / Failed: 2 / Total: 2
```

Failed:

```text
Abstraction_Basic_Suite_Test (10)
Abstraction_Unsaturated_Suite_Test (1)
```

### Failure shape

Both failures are stage2 Rust `E0308` borrow/call-site mismatches. The errors
again point to optimized `Arith.rs` and `Int.rs` functions expecting borrowed
arguments such as `&Num`, while call sites still pass owned `Num` values.

Current diagnosis: the merged abstraction suites are valid stage1 tests. Their
stage2 failures match the optimizer consistency issue observed in FPP and the
first merged targeted suites.

## 2026-07-03 - Merged function suites

### What was migrated

`tests_targeted/functions` was merged into three suite theories. The two
high-level mapping files must remain separate because they define the same
top-level names (`nat_branch`, `nat_delta`, `int_affine`, `int_branch`) under
different numeric encodings.

```text
test/targeted/functions/Function_General_Suite_Test.thy            12 exported definitions
test/targeted/functions/Function_High_Level_Peano_Suite_Test.thy   4 exported definitions
test/targeted/functions/Function_High_Level_Suite_Test.thy         6 exported definitions
```

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/functions
```

Observed summary:

```text
gen summary (test/targeted/functions):
  Exported definitions: Passed: 22 / Failed: 0 / Total: 22
  Theories:             Passed: 3 / Failed: 0 / Total: 3
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/functions
```

Observed summary:

```text
test summary (test/targeted/functions):
  Exported definitions: Passed: 0 / Failed: 22 / Total: 22
  Theories:             Passed: 0 / Failed: 3 / Total: 3
```

Failed:

```text
Function_General_Suite_Test (12)
Function_High_Level_Peano_Suite_Test (4)
Function_High_Level_Suite_Test (6)
```

### Failure shape

`Function_General_Suite_Test` and `Function_High_Level_Peano_Suite_Test` fail
with the same stage2 Rust `E0308` borrow/call-site mismatch seen elsewhere.

`Function_High_Level_Suite_Test` additionally exposes a BigInt import problem in
stage2:

```text
error[E0432]: unresolved import `num_traits::sign::Signed::Signed`
```

The same stage2 crate also has the borrowed-BigInt call mismatch:

```text
expected `&BigInt`, found `BigInt`
```

Current diagnosis: the suite merge is valid for stage1. Stage2 has the general
borrow rewrite issue plus a separate high-level BigInt import path issue.

Suggested fix direction: after the general stage2 borrow rewrite is fixed,
rerun the high-level mapping suite and separately check whether the BigInt
adaptation emits `use num_traits::Signed` instead of
`use num_traits::sign::Signed::{Signed as _}`.

## 2026-07-03 - `types` simple-suite merge conflict

### How it happened

Initial migration put `Set_Pair_Test` and `Type_Tuple_Test` into the same
`Type_Simple_Suite_Test`.

Command:

```sh
make gen DIR=test/targeted/types
```

Observed failure:

```text
Type unification failed: Clash of types "_ set" and "_ => _"
Operator:  map_pair f :: ('b => 'd) => 'a * 'b => 'c * 'd
Operand:   g :: (nat * nat) set
At command "fun" (line 89 of "test/targeted/types/Type_Simple_Suite_Test.thy")
```

### Current diagnosis

`Set_Pair_Test` defines a top-level constant:

```isabelle
definition g :: "(nat \<times> nat) set"
```

`Type_Tuple_Test` later defines:

```isabelle
fun map_pair ... where
  "map_pair f g (x, y) = (f x, g y)"
```

In the original separate theory, `g` is a pattern variable. After merging into
one theory, the already-defined constant `g` changes name resolution and breaks
the function equation.

### Suggested fix direction

Do not put `Set_Pair_Test` and `Type_Tuple_Test` in the same merged theory.
Keep `Set_Pair_Test` in its own suite or rename the local variable in the
migrated copy only if we explicitly decide that such source-level rewriting is
acceptable.

## 2026-07-03 - Merged type suites

### What was migrated

After the `Set_Pair_Test` / `Type_Tuple_Test` name-resolution conflict, the
`types` migration was split into six suite theories:

```text
test/targeted/types/Type_Set_Pair_Suite_Test.thy    1 exported definitions
test/targeted/types/Type_Simple_Suite_Test.thy      12 exported definitions
test/targeted/types/Type_Phantom_Suite_Test.thy     5 exported definitions
test/targeted/types/Type_Recursive_Suite_Test.thy   2 exported definitions
test/targeted/types/Type_Codatatype_Suite_Test.thy  3 exported definitions
test/targeted/types/Type_BigInt_Suite_Test.thy      6 exported definitions
```

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/types
```

Observed summary:

```text
gen summary (test/targeted/types):
  Exported definitions: Passed: 29 / Failed: 0 / Total: 29
  Theories:             Passed: 6 / Failed: 0 / Total: 6
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/types
```

Observed summary:

```text
test summary (test/targeted/types):
  Exported definitions: Passed: 22 / Failed: 7 / Total: 29
  Theories:             Passed: 4 / Failed: 2 / Total: 6
```

Passed:

```text
Type_Codatatype_Suite_Test (3)
Type_Phantom_Suite_Test (5)
Type_Recursive_Suite_Test (2)
Type_Simple_Suite_Test (12)
```

Failed:

```text
Type_BigInt_Suite_Test (6)
Type_Set_Pair_Suite_Test (1)
```

### Failure shape

`Type_Set_Pair_Suite_Test` fails with the familiar stage2 borrow/call-site
mismatch in generated `Set.rs` / `List.rs`:

```text
expected `&A`, found type parameter `A`
expected `&List<A>`, found `List<A>`
```

`Type_BigInt_Suite_Test` exposes a separate BigInt stage2 problem:

```text
error[E0432]: unresolved import `num_traits::sign::Signed::Signed`
error[E0282]: type annotations needed
```

Current diagnosis: the final type-suite split is valid for stage1. The stage2
failures are backend/optimizer issues, not remaining migration conflicts.

## 2026-07-03 - Merged class suites

### What was migrated

`tests_targeted/classes` was split conservatively because several theories reuse
the same class and datatype names (`inc`, `semigroup`, `monoid`, `Nat`,
`plus_Nat`). Non-conflicting class tests were merged into
`Class_Misc_Suite_Test`; the conflicting families remain separate suite units.

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/classes
```

Observed summary:

```text
gen summary (test/targeted/classes):
  Exported definitions: Passed: 19 / Failed: 0 / Total: 19
  Theories:             Passed: 10 / Failed: 0 / Total: 10
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/classes
```

Observed summary:

```text
test summary (test/targeted/classes):
  Exported definitions: Passed: 18 / Failed: 1 / Total: 19
  Theories:             Passed: 9 / Failed: 1 / Total: 10
```

Passed:

```text
Class_Inc_No_Instance_Suite_Test (1)
Class_Inc_Poly_Suite_Test (1)
Class_Inst_Mono_Dispatch_Suite_Test (1)
Class_Misc_Suite_Test (10)
Class_Semigroup_Base_Suite_Test (1)
Class_Semigroup_Nat2_Suite_Test (1)
Class_Semigroup_Nat3_Suite_Test (1)
Class_Semigroup_Nat_Suite_Test (1)
Class_Semigroup_Option_Suite_Test (1)
```

Failed:

```text
Class_Inc_Instance_Suite_Test (1)
```

### Failure shape

`Class_Inc_Instance_Suite_Test` fails in stage2 with the same borrowed-argument
rewrite issue:

```text
plus_nat(n.clone(), one_nat())
expected `&Nat`, found `Nat`
```

Current diagnosis: the class-suite migration is valid for stage1. Stage2 is
mostly healthy for this category; the one failure belongs to the known
borrow/call-site mismatch class.

## 2026-07-03 - `optimization` mut-suite file antiquotation

### How it happened

Initial migration placed all mut optimization tests into:

```text
test/targeted/optimization/Optimization_Mut_Suite_Test.thy
```

Command:

```sh
make gen DIR=test/targeted/optimization
```

Observed failure:

```text
No such file:
"/home/ljy/fm2026/Isabelle2Rust/test/targeted/optimization/Mut_Nat_Test.thy"
line 20 of "test/targeted/optimization/Optimization_Mut_Suite_Test.thy"
```

### Current diagnosis

The source comment in `Mut_Chain_Test.thy` contains an Isabelle file
antiquotation:

```isabelle
\<^file>\<open>Mut_Nat_Test.thy\<close>
```

After merging into a suite theory, that relative file no longer exists next to
the suite, so document antiquotation checking fails before code generation.

### Applied migration correction

In the migrated copy only, replace the file antiquotation with a plain text
reference to `Mut_Nat_Test.thy`. This does not change executable definitions or
exported items.

## 2026-07-03 - Merged optimization suites

### What was migrated

`tests_targeted/optimization` was split by optimization family, with
`Copy_Generic_RCall_Test` kept separate because it overlaps names such as
`flag_pair`, `color`, and `pixel` with smaller copy tests.

```text
test/targeted/optimization/Optimization_Borrow_Suite_Test.thy              24 exported definitions
test/targeted/optimization/Optimization_Copy_Basic_Suite_Test.thy          26 exported definitions
test/targeted/optimization/Optimization_Copy_Generic_RCall_Suite_Test.thy  35 exported definitions
test/targeted/optimization/Optimization_Copy_Borrow_Suite_Test.thy         17 exported definitions
test/targeted/optimization/Optimization_Mut_Suite_Test.thy                 21 exported definitions
```

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/optimization
```

Observed summary after the file-antiquotation migration correction:

```text
gen summary (test/targeted/optimization):
  Exported definitions: Passed: 123 / Failed: 0 / Total: 123
  Theories:             Passed: 5 / Failed: 0 / Total: 5
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/optimization
```

Observed summary:

```text
test summary (test/targeted/optimization):
  Exported definitions: Passed: 78 / Failed: 45 / Total: 123
  Theories:             Passed: 3 / Failed: 2 / Total: 5
```

Passed:

```text
Optimization_Copy_Basic_Suite_Test (26)
Optimization_Copy_Borrow_Suite_Test (17)
Optimization_Copy_Generic_RCall_Suite_Test (35)
```

Failed:

```text
Optimization_Borrow_Suite_Test (24)
Optimization_Mut_Suite_Test (21)
```

### Failure shape

Both failed suites reach stage2 generation and then fail in Rust with the same
borrow/call-site mismatch class. Examples include:

```text
Optimization_Mut_Suite_Test.rs: x = plus_nat(x, one_nat())
expected `&Nat`, found `Nat`

Optimization_Mut_Suite_Test.rs: nat_of_num(Num::Bit0(...))
expected `&Num`, found `Num`
```

Current diagnosis: the optimization-suite migration is valid for stage1. The
remaining failures are stage2 backend consistency issues.

## 2026-07-03 - Merged record suites

### What was migrated

`Rec_Get_Test` and `Rec_Set_Test` share the same recursive `option` datatype, so
they were merged into one suite with a single datatype declaration. The mutually
recursive datatype test remains separate.

```text
test/targeted/records/Record_Option_Suite_Test.thy  2 exported definitions
test/targeted/records/Record_Mutual_Suite_Test.thy  1 exported definitions
```

### Stage 1 result

Command:

```sh
make gen DIR=test/targeted/records
```

Observed summary:

```text
gen summary (test/targeted/records):
  Exported definitions: Passed: 3 / Failed: 0 / Total: 3
  Theories:             Passed: 2 / Failed: 0 / Total: 2
```

### Stage 2 result

Command:

```sh
make test DIR=test/targeted/records
```

Observed summary:

```text
test summary (test/targeted/records):
  Exported definitions: Passed: 3 / Failed: 0 / Total: 3
  Theories:             Passed: 2 / Failed: 0 / Total: 2
```
