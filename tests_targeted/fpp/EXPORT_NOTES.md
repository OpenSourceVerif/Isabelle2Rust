# fpp export-test suite — findings

This suite is built from the book sources in `tests_fpp/` (《函数式程序设计与证明》,
originally for **Isabelle 2021**). Each original `.thy` was copied verbatim into the
mirrored directory here as `<Name>_Test.thy`, the `theory` header renamed, imports
adapted for the Rust session, and an `export_code … in Rust` line appended to drive the
Rust backend over its executable definitions.

**Bar:** a file *passes* when its `export_code … in Rust` runs without error in Isabelle
(stage1 `.rs` generated). Whether the generated Rust then compiles under cargo is a
separate downstream signal, not covered here.

**Result: 37 / 46 build + export OK; 9 fail.** All 9 failures are explained below.

The original `tests_fpp/` files were **not** modified. All adaptations live in the copies.

---

## Adaptations applied to the copies (originals untouched)

- **Imports (all files):** added `"Rust.Rust_Setup"`; rewrote cross-imports of sibling
  theories to their `_Test` names; dropped unresolvable imports `Go.Go_Setup`,
  `"~~/src/HOL/ex/Sqrt"`, `"HOL-Number_Theory.Fib"`.
- **`Highorder_Func_Test`:** the two pre-existing `export_code … in Go` lines were removed
  (Go backend is not set up in the Rust session). The `in Rust`/`in OCaml`/`in Haskell`
  lines are kept.
- **Isabelle 2021→2025 compatibility** (applied to copies only):
  - `Sorted_Less_Test`: `transp_less` → `transp_on_less` (renamed in 2025). This single
    fix unblocked the whole bintree cluster (`List_Ins_Del`, `Set_Specs`, `Isin2`,
    `Tree_Set`, …).
  - `BoundedStack_Test`, `PriorityQueue_Test`: old `{* … *}` text markup → `\<open>…\<close>`
    cartouches (the `{* *}` form was removed after 2018).
  - `Recursion_Test`, `Set_Relation_Test`: added `declare [[quick_and_dirty = true]]` after
    `begin` so the original `termination sorry` / proof `sorry` are accepted and the
    `export_code` step can be reached.
- **Rename fallout fixes** (consequence of the `_Test` theory rename, copies only):
  - `Prog3_Test`: `Prog1.sub`/`Prog2.sub` in `value` commands → `Prog1_Test.*`/`Prog2_Test.*`.
  - `PriorityQueue_Test`: qualified self-references `PriorityQueue.*` in `no_notation` /
    `value` → `PriorityQueue_Test.*`.
- **Inductive `code_pred` predicates** (`Star_Test`, `Big_Step_Test`, `Small_Step_Test`):
  these have no Rust-exportable constant, and a failing `export_code` on them *cascades*
  to their importers (`Compiler`, `Compiler2`, `Small_Step`). The export line was therefore
  dropped from these three base theories (they build but export nothing), which let
  `Compiler_Test` test its real exports.

## Files that intentionally carry no `export_code` (build-only)

Nothing in them is a Rust-exportable constant; they are infrastructure or pure
specification / inductive theories. They build (PASS) but export nothing:

`Less_False_Test` (simproc only), `Sorted_Less_Test` (abbreviation only),
`Set_Specs_Test` & `Priority_Queue_Specs_Test` (locale specs),
`Star_Test`, `Big_Step_Test`, `Small_Step_Test` (inductive `code_pred` predicates).

---

## The 9 failures, grouped by cause

### A. Rust backend cannot print the requested type (genuine backend findings)
- **`Set_Relation_Test`** — `export_code Set0 Set5 Set6 graph1 graph2 Vset`: backend
  raises `exception Match (code_printer.ML:359)` on the HOL `set` type. (`Id`/`Id_int`
  additionally need `int :: enum`.) → **The Rust backend has no `set` support.**
- **`Compiler2_Test`** — `succs`/`isuccs`/`exits` return `int set`; Wellsortedness /
  `set` again. The theory has no non-`set` executable constant (`exec_n` is an
  existential predicate).
- **`AVL_Set_Code_Test`** — `export_code … balL balR insert …`: backend raises
  `exception Match (code_printer.ML:359)`. The `balL`/`balR` definitions use
  **non-exhaustive nested `case`** (no `Leaf` branch); the Rust printer crashes on the
  resulting partial match. → **backend bug on incomplete-pattern functions.**
- **`AVL_Set_Test`** — cascades from `AVL_Set_Code_Test` (imports it). `avl` itself is clean.

### B. Locale-local constants have no code equations (Isabelle codegen limitation)
- **`Locale_Test`** — `db_list.*`, `db_map.*`: "No code equations …". Constants defined
  inside a `locale` are not code-registered without an interpretation at a concrete type.
- **`BoundedStack_Test`** — same: `bstack_list.*`, `bstack_type.*` are locale-local.
  (Contrast `PriorityQueue_Test`, whose operations are top-level over a `typedef` with
  `[code abstype]` — **that one exports fine**, a useful positive datapoint.)

### C. Original source incompatible with Isabelle 2025 (pre-existing, not a backend issue)
- **`Function_Test`** — first definition `sqrt r ≡ … root 2 r` fails: `root` (`NthRoot`)
  is not in scope under `HOL.Real`. Adding `Complex_Main` fixes `root` but then exposes
  `Fun.swap` (removed/renamed in 2025) and a proof that no longer applies. Not recoverable
  without editing the original definitions/proofs. Most of `Function`'s exports
  (`Pred minus_nat fun1 suc pred …`) are otherwise clean.
- **`AlgebraicStructure_Test`** — original uses `sorry` (isort termination, `functor …
  sorry`) **and** `thm AlgebraicStructure.list.comp` references a fact whose name changed
  in 2025. Mostly monad/`set`/IO/`real` code that is non-executable anyway.
- **`search_Test`** — the original `search.thy` contains an **incomplete/broken proof**
  (≈ line 209: `then show ?case / then have …` with no statement). The theory does not
  elaborate, so export is never reached. Functions `liner_search*`/`binary_search*` are
  otherwise exportable.

---

## Per-definition exclusions flagged for discussion (不可导出, 单独讨论)

For files that **do** pass, definitions that depend on non-codegen features were left out
of `export_code` (listed here so nothing is silently dropped):

- **`Tree_Test`**: excluded `subtrees`, `bst_wrt`, `heap` (use `'a set` / `set_tree`);
  `bst` is an abbreviation. Exported the clean tree/`height`-class functions.
- **`Tree2_Test`**: excluded `set_tree`, `bst` (`set`). Exported `inorder`.
- **`Types_Test`**: excluded `rel1`/`conn1`/`Agraph` (axiomatized `Vertex` / `set`),
  `coord7`/`coord9`/`coord10` (`real`), `SUC`/`ADD`/`One`/`Two`/`Three`/`xorBOOL`
  (`typedef`/`axiomatization` on `Even`/`three`/`BOOL`).
- **`Function_Test`** (had it built): would exclude `func`/`sqrt` (`set`/`real`/`root`),
  `add2` (`real`), `suc_inv`/`suc2_inv`/`f6_inv` (`the_inv`), `kvs3`/`kvs4` (`set`).
- **`AlgebraicStructure_Test`** (had it built): would exclude the `set`/state/IO monads,
  `real` (`vlen`/`list3`), and `functor map_F/map_t` (`typedef` + `sorry`); keep the
  option/list-monad and pure-list/functor maps.
- **`Recursion_Test`**: excluded `ev` (`2*n` pattern), `fib3` (`n+2` pattern),
  `gcd`/`check` (conditional/guarded equations) — not constructor-pattern executable.
- **`Highorder_Func_Test`**: excluded `limit` (`real` + unbounded quantifier).
- **`Set_Relation_Test`**: dropped `Id_int` (needs `int :: enum`); the remaining
  finite-set probes still hit the `set` backend `Match` crash (see A).

---

## Reproduce

```
make build TEST_DIR=tests_targeted/fpp/<sub> TEST_THEORY=<Name>_Test   # one file
# or build every fpp file and tally pass/fail (Isabelle-export bar):
#   loop `make build_silent` over tests_targeted/fpp/**/*_Test.thy
```
