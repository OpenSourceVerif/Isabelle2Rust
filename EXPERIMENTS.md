# Isabelle2Rust Experiment Record

This file is the long-term source of truth for experiments run from the
Isabelle2Rust repository.  Entries record both successful results and failed
attempts.

Before rerunning an experiment, execute:

```sh
scripts/hol-experiment-fingerprint.sh
```

If its value matches the latest successful HOL-Codegenerator entry below, reuse
the recorded generated artifacts and measurements.  Rerun the generation and
optimization only after this fingerprint changes.  Read-only recounting of an
unchanged artifact does not require a rerun.

## 2026-08-06: Eta-reduction removal and Stage-2-only RQ3 rerun

The closure-cleanup pass no longer rewrites
`Rc::new(move |x| (*f(v))(x))` to `f(v)`.  The rewrite can move evaluation of
`f(v)` from closure invocation to closure construction and therefore does not
preserve divergence in general.  Closure cleanup is now restricted to removing
generated owned-capture aliases.

Stage-1, OCaml, and original-system artifacts and measurements remained
frozen.  Only the four Stage-2 configurations were regenerated, validated, and
remeasured from the accepted Stage-1 artifacts.  The resulting snapshots are:

- SBPF: `evaluation/performance/results/20260806-173656+0800`, reusing the
  accepted baseline rows from `20260801-063556+0800`;
- x64: `evaluation/performance/results/x64-20260806-174144+0800`, reusing the
  accepted baseline rows from `x64-20260801-063336+0800`.

The first SBPF attempt exposed a latent ownership issue: without eta-reduction,
generated `_cap` values can remain inside escaping `move` closures, but borrow
analysis had converted some of those bindings into aliases of borrowed pattern
fields.  The final optimizer keeps generated `_cap` bindings owned and includes
a regression test for this case.  The complete optimizer suite then passed
(163 library tests and 2 CLI tests), and `cargo fmt --check` succeeded.

All final Stage-2 configurations passed differential validation: 146/146
SBPF-program cases, 6,000/6,000 SBPF-instruction vectors, and 6,000/6,000
x64-stepper vectors.  Relative to the previously accepted full Stage-2
measurements, the eta-reduction-free full configuration changed as follows:

| Workload | Old runtime (s) | New runtime (s) | Runtime change | Old allocation | New allocation | Allocation change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SBPF-program | 0.006857078 | 0.010580467 | +54.3% | 0.044833980 MiB/case | 0.096717416 MiB/case | +115.7% |
| SBPF-instruction | 0.053390560 | 0.079076947 | +48.1% | 15.784656250 KiB/vector | 22.234416667 KiB/vector | +40.9% |
| x64-stepper | 0.009731201 | 0.010296761 | +5.8% | 2.490575521 KiB/step | 2.742649740 KiB/step | +10.1% |

Despite this cost, final Stage-2 remains approximately 7,727x, 66.9x, and
3.00x faster than frozen Stage-1 on SBPF-program, SBPF-instruction, and
x64-stepper, respectively.  The remaining closure cleanup has no measurable
performance contribution on these workloads: full and minus-Closure have
identical allocation counts, and their paired median runtime ratios differ by
less than 1%.

For code quality, all 92 tracked Stage-2 crates were regenerated from frozen
Stage-1 and compiled successfully before running the Stage-2-only Clippy audit.
The result remains 16 diagnostics with no failed crates: 1
`overly_complex_bool_expr`, 2 `too_many_arguments`, 4 `type_complexity`, and 9
`unconditional_recursion`.  Thus removing eta-reduction changes neither the
paper's Stage-2 Clippy total nor its lint distribution.

## 2026-07-16: HOL-Codegenerator Stage-1 and Stage-2

### Reproduction key

- Experiment fingerprint:
  `a9f2855b04fba19a54c977f3b206625d1191027ffa0a731f7e06ce877989d4cf`
- Base Git commit:
  `4e37dba79ab7e27869f223dd378d3213392dbef0`
- Toolchain: Isabelle2025, rustc 1.93.0-nightly
  (`b84478a1c 2025-11-30`), cargo 1.93.0-nightly
  (`2a7c49606 2025-11-25`), cloc 1.90.
- LOC means cloc's Rust `code` column: nonblank, non-comment lines in `.rs`
  files, with `target` directories excluded and `--skip-uniqueness` enabled.
- The definition count is Isabelle's wildcard export-entry count.  The Thingol
  function-node count is also retained below as a lower-level cross-check, but
  is not used as the paper's exported-definition metric.

### Successful final results

| Workload | Exported definitions | Thingol function nodes | Stage-1 Rust files | Stage-1 LOC | Stage-2 Rust files | Stage-2 LOC | Stage-1 `.clone()` | Stage-2 `.clone()` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Generate` | 3,147 | 2,940 | 197 | 52,855 | 197 | 46,641 | 17,343 | 5,130 |
| `Generate_Binary_Nat` | 3,145 | 2,936 | 198 | 53,339 | 198 | 45,710 | 17,162 | 4,674 |
| Stress total | not summed because the variants overlap | not summed | 395 | 106,194 | 395 | 92,351 | 34,505 | 9,804 |
| `Code_Test_Rust` smoke test | 5 | not measured | 6 | 169 | 6 | 175 | 62 | 45 |

The two stress crates reduce aggregate Rust LOC by 13.0% and explicit
`.clone()` sites by 71.6% from Stage-1 to Stage-2.  Both Stage-1 and both
Stage-2 stress crates compile successfully.  The Stage-1 and Stage-2 smoke
crates also compile and run successfully.

Commands and resource results:

- Final persistent `make hol-stress`: exit 0, 237.36 s elapsed, 5,781,272 KiB
  maximum RSS.  Both wildcard exports were extracted under
  `test/HOL_Codegenerator/stage1` and compiled with Cargo.
- `make hol-gcd`: exit 0, 17.70 s elapsed, 1,301,244 KiB maximum RSS.  The
  generated smoke executable ran without an assertion failure.
- Fixed `Generate` Stage-2 run: exit 0, 18.25 s elapsed, 836,644 KiB maximum
  RSS.
- `Generate_Binary_Nat` Stage-2 run: exit 0, 18.64 s elapsed, 821,988 KiB
  maximum RSS.
- `Code_Test_Rust` Stage-2 run: exit 0, 2.50 s elapsed, 215,308 KiB maximum
  RSS.  Its generated executable was then run successfully.
- Full optimizer regression suite: 69 passed, 0 failed.

### Clippy integration into the Unit/FPP corpus (2026-07-17)

The experiment fingerprint still matched the successful Stage-1/Stage-2
record, so this analysis reused the existing generated crates without rerunning
Isabelle or the optimizer.  Clippy 0.1.93 was run with `clippy::all` on the two
HOL-Codegenerator stress variants.  The smoke crate was not included in this
library-scale paper corpus.

| Clippy lint | HOL Stage-1 | HOL Stage-2 | Unit/FPP + HOL Stage-1 | Unit/FPP + HOL Stage-2 |
| --- | ---: | ---: | ---: | ---: |
| `clone_on_copy` | 588 | 126 | 855 | 126 |
| `type_complexity` | 1,125 | 1,145 | 1,136 | 1,156 |
| `match_single_binding` | 218 | 0 | 223 | 0 |
| `double_parens` | 558 | 7 | 561 | 7 |
| `needless_bool` | 0 | 0 | 2 | 0 |
| `unconditional_recursion` | 18 | 18 | 19 | 19 |
| `collapsible_match` | 268 | 10 | 268 | 10 |
| `if_same_then_else` | 4 | 4 | 4 | 4 |
| `nonminimal_bool` | 13 | 13 | 13 | 13 |
| `overly_complex_bool_expr` | 2 | 2 | 2 | 2 |
| `too_many_arguments` | 4 | 4 | 4 | 4 |
| `blocks_in_conditions` | 0 | 2 | 0 | 2 |
| `let_and_return` | 0 | 78 | 0 | 78 |
| `only_used_in_recursion` | 0 | 2 | 0 | 2 |
| Total | 2,798 | 1,411 | 3,087 | 1,423 |

Warning: a subsequent audit found that this historical summary is incomplete.
It omits 153 HOL Stage-1 `collapsible_else_if` diagnostics and 28 Unit/FPP
Stage-2 `let_and_return` diagnostics.  The saved Unit/FPP Stage-1 count also
does not retain enough manifest/span information to prove that it used the
same crate selection as Stage-2.  Consequently, the combined totals and
reduction above must not be reused in the paper until the Unit/FPP manifest
selection has been reconstructed and recorded explicitly.  The paper's stated
92-case scope also disagrees with the 89 crate pairs in the LOC experiment
below.

The original summary inferred a paper-level Clippy reduction of 53.9%; that
percentage is invalid pending the manifest-aligned recount described above.
The separately counted explicit `.clone()` sites fall from 40,519 to 10,468,
a 74.2% reduction.

The first reporting pipeline attempted to use `jq`, which is not installed on
this system.  It exited 127 and caused Cargo to report a broken pipe.  The
Clippy runs were repeated successfully with a streaming Python JSON parser.

### `type_complexity` differential audit (2026-07-17)

The current fingerprint
`b85cc0ee96e82e350e51d50d0767ba02509093611a19df395340402561b3e446`
matches the Stage-2 record below.  Existing artifacts were therefore reused;
Isabelle and the optimizer were not rerun.  Recounting unique primary Clippy
diagnostics reproduced `562 -> 572` for `Generate` and `563 -> 573` for
`Generate_Binary_Nat`, hence `1,125 -> 1,145` in aggregate.  There are no
duplicate Cargo messages in these counts.

Each stress variant has the same ten new diagnostics:

| Stage-2 source context | New diagnostics per variant | Cause |
| --- | ---: | --- |
| `Quickcheck_Exhaustive::{cps_single_copy, neg_bound_cps_single_copy, pos_bound_cps_single_copy}` | 4 | Copy specialization duplicates three complex function signatures and one typed-closure annotation. |
| `Random_Pred::single_copy` | 1 | Copy specialization duplicates a complex function signature. |
| `Random_Sequence::{single_copy, neg_single_copy, pos_single_copy}` | 4 | Copy specialization duplicates three complex function signatures and one typed-closure annotation. |
| `RBT_Impl::gen_entries` | 1 | Borrow optimization changes a score-250 owned parameter type to a score-251 reference type, crossing Clippy's default threshold of 250. |

Thus, nine diagnostics per variant are duplicated by reachable `_copy`
functions, and one is introduced by the borrowed `gen_entries` signature.
This is a real lint-count regression, although it is localized rather than a
general increase in the structural complexity of existing types.  The
preferred fix is a deterministic generic type-alias extraction pass shared by
the original and `_copy` functions and applied to typed closures as well as
function signatures.  The current RustLightAST `TypeAlias` representation must
first preserve generic parameters.  Skipping these Copy/Borrow optimizations
can enforce a short-term no-regression gate but sacrifices useful
optimizations; `#[allow]` and a raised Clippy threshold would only hide the
problem and are not accepted fixes.

### Failed attempts and warnings

1. The first `make hol-stress` run used the old temporary `checking Rust`
   workflow.  It succeeded in 147.79 s with 5,703,640 KiB maximum RSS, but its
   generated checker directories were temporary and could not be used for
   reproducible LOC measurement.  The workflow now exports both crates into
   persistent Stage-1 directories and compiles those exact files.
2. The first Stage-2 attempt for `Generate` aborted with `thread 'main' has
   overflowed its stack` and exit code 2 after 2.53 s.  The Makefile now runs
   the optimizer with a 65,536 KiB stack (`OPT_STACK_KB`).
3. With the larger stack, the next `Generate` optimization emitted all 197
   files but Cargo failed with `E0382: borrow of moved value: n` in
   `Word.rs::word_rotr`.  M-LastUse had removed a clone from a block initializer
   whose tuple binding shadowed the outer `n`.  The liveness pass now preserves
   enclosing-scope liveness across such shadowing bindings, with a regression
   test.  Regeneration then passed.
4. Optimizing the smoke crate reports one non-fatal warning: generated
   `main.rs` is passed through unoptimized because the RustLightAST parser does
   not support its statement macro.  Cargo build and execution both pass.
5. The original static export-item counter displayed each wildcard `_` as one
   exported definition in `make opt` progress output.  This affected only the
   progress label.  The paper counts come from the Isabelle/ML wildcard graph.
   The Makefile now labels these cases as `wildcard export` instead of showing
   the misleading value.

### Artifact locations

- Stage-1 stress:
  `test/HOL_Codegenerator/stage1/{Generate,Generate_Binary_Nat}/export1`
- Stage-2 stress:
  `test/HOL_Codegenerator/stage2/{Generate,Generate_Binary_Nat}`
- Smoke artifacts:
  `test/HOL_Codegenerator/{stage1/Code_Test_Rust/export1,stage2/Code_Test_Rust}`

## 2026-07-17: Conservative Stage-2 bound cleanup

The Stage-1 artifacts were reused because this change affects only the
optimizer.  All Stage-2 crates were regenerated with experiment fingerprint
`b85cc0ee96e82e350e51d50d0767ba02509093611a19df395340402561b3e446`.
LOC uses the same `cloc --skip-uniqueness --exclude-dir=target` Rust-code
column as the HOL-Codegenerator record above.

| Corpus | Crate pairs | Stage-1 Rust LOC | Stage-2 Rust LOC | Reduction |
| --- | ---: | ---: | ---: | ---: |
| Unit | 51 | 8,576 | 8,001 | 6.7% |
| FPP | 36 | 21,809 | 20,406 | 6.4% |
| HOL-Codegenerator stress | 2 | 106,194 | 92,203 | 13.2% |
| Total | 89 | 136,579 | 120,610 | 11.7% |

The optimizer regression suite passed 75 tests.  Cargo builds passed for all
51 Unit Stage-2 crates, all 36 FPP Stage-2 crates, the two HOL-Codegenerator
stress crates, and the `Code_Test_Rust` smoke crate.  The Unit corpus currently
contains 434 exported definitions and the FPP corpus contains 328, for 762 in
total.

## 2026-07-17: General removal of HOL Stage-2 `clone_on_copy`

This optimizer-only experiment reused the persistent Stage-1 artifacts.  The
Isabelle export was not rerun.  The implementation contains no symbol-,
module-, or HOL-Codegenerator-specific exception.  It extends the existing
copy analysis in three general ways: it traverses implementation methods and
honors implementation-level `Copy` bounds, parses closure-parameter type
annotations through the full RustLightAST type parser and binds destructured
patterns recursively, and propagates inferred types through block and `if`
tail expressions conservatively.

- Experiment fingerprint:
  `f41cc7dee681a48622d7022da2a7a5914eca1275a831235b1f42a39bd64516a8`
- Base Git commit: `4e37dba79ab7e27869f223dd378d3213392dbef0`
- Toolchain: rustc 1.93.0-nightly (`b84478a1c 2025-11-30`), cargo
  1.93.0-nightly (`2a7c49606 2025-11-25`), Clippy 0.1.94
  (`4a4ef493e3 2026-03-02`), and cloc 1.90.
- Full optimizer regression suite: 79 passed, 0 failed.
- `Generate` Stage-2 regeneration and Cargo build: exit 0, 17.04 s elapsed,
  835,392 KiB maximum RSS.
- `Generate_Binary_Nat` Stage-2 regeneration and Cargo build: exit 0, 15.90 s
  elapsed, 850,900 KiB maximum RSS.

Clippy was run on both regenerated Stage-2 crates with
`RUSTC_BOOTSTRAP=1 cargo +stable clippy -- -W clippy::all`.  Diagnostics were
counted as unique primary Cargo JSON messages.

| Workload | Previous `clone_on_copy` | Current `clone_on_copy` | Current all Clippy diagnostics |
| --- | ---: | ---: | ---: |
| `Generate` | 63 | 0 | 648 |
| `Generate_Binary_Nat` | 63 | 0 | 637 |
| Stress total | 126 | 0 | 1,285 |

All 126 previously reported HOL Stage-2 `clone_on_copy` diagnostics are
eliminated.  The aggregate HOL Stage-2 Clippy count therefore changes from
1,411 to 1,285; all other lint-category counts are unchanged.  Both Clippy
commands exited successfully.  No failed optimizer test, Stage-2 generation,
Cargo build, or Clippy command occurred in this experiment.

| Workload | Stage-2 Rust files | Stage-2 LOC | Stage-2 `.clone()` sites |
| --- | ---: | ---: | ---: |
| `Generate` | 197 | 46,648 | 5,068 |
| `Generate_Binary_Nat` | 198 | 45,717 | 4,612 |
| Stress total | 395 | 92,365 | 9,680 |

Relative to the unchanged Stage-1 totals of 106,194 LOC and 34,505 explicit
`.clone()` sites, the regenerated Stage-2 artifacts reduce LOC by 13.0% and
explicit clone sites by 71.9%.  The explicit-site count falls by 124 rather
than 126 because the optimizer's general call-specialization and method
traversal can change other, non-`clone_on_copy` clone sites.  The Clippy result
is the authoritative check for this task: no `clone_on_copy` diagnostic remains
in either HOL Stage-2 crate.

### Manifest-aligned RQ3 recount

The paper corpus was reconstructed explicitly before updating RQ3.  It uses
the greatest-numbered Rust `exportN` directory for each of the 50 Unit
`*_Test.thy` theories, `paper_example`, and each of the 36 FPP theories that
contains an executable `export_code` command.  Adding the two
HOL-Codegenerator stress variants gives 89 Stage-1/Stage-2 crate pairs.  This
selection reproduces the recorded pre-change Unit and FPP LOC exactly:
8,576/8,001 and 21,809/20,406, respectively.

Because the optimizer changed, all 87 Unit/FPP Stage-2 crates were regenerated
from the persistent Stage-1 artifacts.  All 87 optimizer runs and Cargo builds
passed.  Isabelle was not rerun.  Clippy 0.1.94 was then rerun on all 178
manifests in the 89 crate pairs.  Unique primary diagnostics were keyed by
stage, manifest, lint code, source file, line, column, and message.  All 178
Clippy commands passed.

| Clippy lint | Stage-1 | Stage-2 | Reduction |
| --- | ---: | ---: | ---: |
| `clone_on_copy` | 855 | 0 | 100% |
| `type_complexity` | 1,136 | 1,156 | -1.8% |
| `match_single_binding` | 223 | 0 | 100% |
| `double_parens` | 561 | 7 | 98.8% |
| `needless_bool` | 2 | 0 | 100% |
| `unconditional_recursion` | 19 | 19 | 0% |
| `collapsible_match` | 268 | 10 | 96.3% |
| `if_same_then_else` | 4 | 4 | 0% |
| `nonminimal_bool` | 13 | 13 | 0% |
| `overly_complex_bool_expr` | 2 | 2 | 0% |
| `too_many_arguments` | 4 | 4 | 0% |
| `blocks_in_conditions` | 0 | 2 | introduced |
| `let_and_return` | 0 | 90 | introduced |
| `only_used_in_recursion` | 0 | 2 | introduced |
| Total | 3,087 | 1,309 | 57.6% |

The Stage-1 total consists of 3,068 Clippy-coded diagnostics and 19 rustc
`unconditional_recursion` diagnostics reported by the same Clippy commands;
the corresponding Stage-2 split is 1,290 and 19.  In both stages, 18 of the
recursion diagnostics come from HOL-Codegenerator and one from FPP.  No other
non-Clippy coded warning occurs in this corpus.

| Corpus | Crate pairs | Stage-1 LOC | Stage-2 LOC | Stage-1 `.clone()` | Stage-2 `.clone()` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unit | 51 | 8,576 | 8,001 | 1,680 | 185 |
| FPP | 36 | 21,809 | 20,406 | 4,329 | 480 |
| HOL-Codegenerator stress | 2 | 106,194 | 92,365 | 34,505 | 9,680 |
| Total | 89 | 136,579 | 120,772 | 40,514 | 10,345 |

Across the aligned corpus, Stage-2 reduces generated Rust LOC by 11.6% and
explicit `.clone()` sites by 74.5%.  The HOL-specific LOC reduction is 13.0%.

The first aligned Clippy attempt passed 40 manifests and then stopped before
linting `MutTrees_Test` because that generated Stage-1 crate had no
`Cargo.lock` and the command used `--locked`.  The successful rerun retained
`--locked` for existing lockfiles and used Cargo's offline dependency
resolution for the one missing lockfile.  It made no network request and
completed all 178 manifests.  An earlier orchestration command containing a
disallowed temporary-file removal was rejected before execution; it changed no
artifact and produced no experimental result.

The first isolated paper-build check exited 12 because `minted` requires
LaTeX's `-shell-escape` option.  Repeating the check with that required option
succeeded and produced the 39-page PDF under
`/tmp/isabelle2rust-paper-check`; the updated RQ1 and RQ3 sources introduced no
LaTeX error.

## 2026-07-17: Removal of the remaining Stage-2 `double_parens`

This optimizer-only experiment reused all persistent Stage-1 artifacts.  The
RustLightAST printer changed, so all 89 manifest-aligned Stage-2 crates were
regenerated before the final Clippy recount.  Isabelle was not rerun.

- Experiment fingerprint:
  `63890ed740d4dcf1833dc1982d8e8ef47e148b740e9c39f0efa6d25e6d83f71e`
- Toolchain: Clippy 0.1.94 (`4a4ef493e3 2026-03-02`); the Rust and Isabelle
  versions are unchanged from the preceding manifest-aligned experiment.
- RustLightAST regression suite: 9 passed, 0 failed.
- Optimizer regression suite: 79 passed, 0 failed.

The seven pre-fix diagnostics were audited individually:

| # | Workload and pre-fix Stage-2 primary span | Stage-1 source | Transformation that exposed the redundant parentheses |
| ---: | --- | --- | --- |
| 1 | `Generate/Omega_Words_Fun.rs:26:18`, `conc` | `Omega_Words_Fun.rs:27` | A one-arm tuple `match` became a block inside `(*x)(...)`. |
| 2 | `Generate/Omega_Words_Fun.rs:63:14`, `build` | `Omega_Words_Fun.rs:57` | A one-arm tuple `match` became a block inside `(*w)(...)`. |
| 3 | `Generate/Old_Datatype.rs:30:26`, `push` | `Old_Datatype.rs:34` | A one-arm tuple `match` became a block inside `(*h)(...)`. |
| 4 | `Generate/Extended_Nat.rs:232:28`, `Enat::minus` | `Extended_Nat.rs:212` | A one-arm tuple `match` became a block inside `Enat::Enat(...)`. |
| 5 | `Generate/Arith.rs:791:26`, `case_nat` | `Arith.rs:893` | A one-arm tuple `match` became a block inside `(*g)(...)`. |
| 6 | `Generate/Arith.rs:1413:5345`, `BigInt::term_ofa` | `Arith.rs:1480` | M-LastUse changed `(-i.clone())` to `(-i)` but retained the explicit argument wrapper. |
| 7 | `Generate_Binary_Nat/Arith.rs:1495:5345`, `BigInt::term_ofa` | `Arith.rs:1602` | The same M-LastUse path retained the explicit wrapper around `-i`. |

For the first five, the parser preserved the explicit Stage-1 wrapper as
`Parenthesized(Match)`.  The match cleanup replaced only the inner match with a
block, leaving `Parenthesized(Block)`, which the printer emitted as `(({...}))`
because the call supplied another pair of delimiters.  The final two were
`Parenthesized(UnaryOp)` nodes.  M-LastUse correctly removed a final-use clone
from the inner expression but had no reason to change its syntactic wrapper.
These are two manifestations of the same missing call-argument printing rule,
not seven ownership-analysis failures.  The five block cases originate in the
BigInt natural-subtraction template; the two unary cases originate in the
BigInt integer-negation template.

The fix is in `RustLightAST/src/rustlight_print.rs::generate_call_argument`.
It removes only leading `Parenthesized` nodes at the root of a call or method
argument, where the call delimiters already delimit the complete expression.
It does not remove parentheses globally, which could change binary-expression
precedence.  Tuple expressions retain their own structural parentheses.  New
printer tests cover block and unary arguments and verify tuple preservation;
the existing cast test also continues to pass.

Regeneration and verification results:

- `Generate`: optimization and Cargo build exit 0, 18.75 s elapsed, 881,536
  KiB maximum RSS.
- `Generate_Binary_Nat`: optimization and Cargo build exit 0, 18.71 s
  elapsed, 820,888 KiB maximum RSS.
- The other 87 aligned crates: 87 optimizer runs and 87 Cargo builds passed
  (Unit 51/51 and FPP 36/36).
- Final Stage-2 Clippy recount: all 89 commands passed and produced 1,302
  unique primary diagnostics.  Neither HOL crate nor any other aligned crate
  reports `clippy::double_parens`.
- The paper rebuilt successfully with `latexmk -pdf -shell-escape`: exit 0,
  39 pages.  The TeX log retained a non-fatal minted cleanup message,
  `rm: cannot remove '0.main.pyg': No such file or directory` (reported
  internally as system code 256); it did not prevent PDF generation.

| Clippy lint | Stage-1 | Stage-2 | Reduction |
| --- | ---: | ---: | ---: |
| `clone_on_copy` | 855 | 0 | 100% |
| `type_complexity` | 1,136 | 1,156 | -1.8% |
| `match_single_binding` | 223 | 0 | 100% |
| `double_parens` | 561 | 0 | 100% |
| `needless_bool` | 2 | 0 | 100% |
| `unconditional_recursion` | 19 | 19 | 0% |
| `collapsible_match` | 268 | 10 | 96.3% |
| `if_same_then_else` | 4 | 4 | 0% |
| `nonminimal_bool` | 13 | 13 | 0% |
| `overly_complex_bool_expr` | 2 | 2 | 0% |
| `too_many_arguments` | 4 | 4 | 0% |
| `blocks_in_conditions` | 0 | 2 | introduced |
| `let_and_return` | 0 | 90 | introduced |
| `only_used_in_recursion` | 0 | 2 | introduced |
| Total | 3,087 | 1,302 | 57.8% |

The 1,302 Stage-2 total comprises 1,283 Clippy-coded diagnostics and 19 rustc
`unconditional_recursion` diagnostics emitted by the same commands.  The
printer change removes exactly the seven audited diagnostics; all other lint
counts are unchanged.  The regenerated Stage-2 size and clone measurements
also remain unchanged:

| Corpus | Stage-2 Rust files | Stage-2 LOC | Stage-2 `.clone()` sites |
| --- | ---: | ---: | ---: |
| Unit | 197 | 8,001 | 185 |
| FPP | 275 | 20,406 | 480 |
| HOL-Codegenerator stress | 395 | 92,365 | 9,680 |
| Total | 867 | 120,772 | 10,345 |

Failed diagnostic/orchestration attempts, all without source or artifact
changes:

1. One diagnostic-extraction attempt used unavailable `jq` and exited 127;
   the successful recount used Perl's streaming `JSON::PP` parser.
2. The first patch command used an incorrectly resolved sibling path and
   failed before editing a file; the corrected workspace-relative path was
   then applied.
3. The first 87-crate orchestration tool call contained an unescaped template
   expression and failed in the JavaScript wrapper before the shell command
   ran.  The corrected command then completed 87/87 runs successfully.

## 2026-07-17: Elimination of Stage-2 `let_and_return`

This optimizer-only experiment reused the current Stage-1 artifacts.  A
module-wide postprocessing step now recursively collapses a trailing immutable,
untyped identifier binding when the block returns either that identifier or its
`.clone()` result.  The cleanup runs after last-use clone rewriting, so it
handles both identity aliases such as `let y = x; y` and borrow-induced aliases
such as `let y = p.as_ref(); y.clone()` without changing the analysis-only
function copies used by borrow inference.

- Experiment fingerprint:
  `06b9b65c321c8bfed025d402926bebd4331584ea508d860fd5343b5525f7b381`
- Optimizer regression suite: 88 passed, 0 failed.
- All 101 current Stage-2 test crates regenerated and passed Cargo build.
- Manifest-aligned Stage-1 Clippy recount: 89 passed, 0 failed, with 3,140
  unique primary diagnostics.
- Manifest-aligned Stage-2 Clippy recount: 89 passed, 0 failed, with 1,193
  unique primary diagnostics and no `clippy::let_and_return` diagnostic.
- All 101 current `test/**/stage2/*/Cargo.toml` crates passed Clippy.  Across
  those manifests, `clippy::let_and_return` occurs zero times.

The current paired RQ3 recount is:

| Clippy lint | Stage-1 | Stage-2 | Reduction |
| --- | ---: | ---: | ---: |
| `clone_on_copy` | 855 | 0 | 100% |
| `type_complexity` | 1,136 | 1,154 | -1.6% |
| `match_single_binding` | 223 | 0 | 100% |
| `double_parens` | 561 | 0 | 100% |
| `needless_bool` | 2 | 0 | 100% |
| `unconditional_recursion` | 19 | 19 | 0% |
| `collapsible_match` | 325 | 10 | 96.9% |
| `if_same_then_else` | 0 | 0 | -- |
| `nonminimal_bool` | 13 | 0 | 100% |
| `overly_complex_bool_expr` | 2 | 2 | 0% |
| `too_many_arguments` | 4 | 4 | 0% |
| `blocks_in_conditions` | 0 | 2 | introduced |
| `let_and_return` | 0 | 0 | -- |
| `only_used_in_recursion` | 0 | 2 | introduced |
| Total | 3,140 | 1,193 | 62.0% |

This is an end-to-end recount of the current checkout, not an isolated
ablation.  In particular, the `nonminimal_bool` reduction reflects the
already-present Boolean cleanup rather than the trailing-let rule itself.

The same 89-crate pairing contains 41,089 Stage-1 and 10,384 Stage-2
`.clone()` sites, a 74.7% reduction.  In the two HOL-Codegenerator stress
variants, aggregate Rust LOC changes from 107,504 to 93,179, a 13.3%
reduction.  These paired measurements replace the earlier 3,087/1,302 table,
whose Stage-1 and Stage-2 roots predated the latest generated artifacts.

## 2026-07-18: Standard-only RQ3 Clippy recount

The RQ3 code-quality corpus now matches RQ1: 51 Unit crate pairs, 36 FPP
crate pairs, and the standard `Generate` HOL-Codegenerator pair.  The
`Generate_Binary_Nat` variant is excluded.  `Generate` was regenerated from
the current source through Stage-1 and Stage-2, and both crates passed Cargo
build.  The experiment fingerprint was
`75c57c47605e2102af2b5185f73be52c689d6a269cee6c389def02f15fdbe2c5`.

Clippy 0.1.94 was run with `clippy::all` on all 176 manifests in the 88
Stage-1/Stage-2 crate pairs.  Every command passed.  Unique primary diagnostics
were keyed by stage, manifest, lint code, source location, and message.

| Clippy lint | Stage-1 | Stage-2 | Reduction |
| --- | ---: | ---: | ---: |
| `clone_on_copy` | 561 | 0 | 100% |
| `type_complexity` | 573 | 582 | -1.6% |
| `match_single_binding` | 218 | 0 | 100% |
| `double_parens` | 288 | 0 | 100% |
| `needless_bool` | 2 | 0 | 100% |
| `unconditional_recursion` | 9 | 9 | 0% |
| `collapsible_match` | 164 | 5 | 97.0% |
| `nonminimal_bool` | 10 | 0 | 100% |
| `overly_complex_bool_expr` | 1 | 1 | 0% |
| `too_many_arguments` | 2 | 2 | 0% |
| `blocks_in_conditions` | 0 | 1 | introduced |
| Total | 1,828 | 600 | 67.2% |

| Corpus | Crate pairs | Stage-1 LOC | Stage-2 LOC | Stage-1 `.clone()` | Stage-2 `.clone()` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unit | 51 | 8,641 | 8,042 | 1,689 | 187 |
| FPP | 36 | 21,809 | 20,389 | 4,329 | 464 |
| HOL-Codegenerator (`Generate`) | 1 | 53,504 | 47,049 | 17,625 | 5,095 |
| Total | 88 | 83,954 | 75,480 | 23,643 | 5,746 |

## 2026-07-18: Eliminate the remaining Stage-2 `double_parens`

This optimizer-output experiment reused the unchanged persistent Stage-1
artifacts.  The shared RustLightAST printer changed, so both HOL-Codegenerator
Stage-2 stress crates were regenerated and rebuilt.  Isabelle and Stage-1 were
not rerun.

- Experiment fingerprint:
  `63890ed740d4dcf1833dc1982d8e8ef47e148b740e9c39f0efa6d25e6d83f71e`
- Toolchain: Clippy 0.1.94 (`4a4ef493e3 2026-03-02`).
- RustLightAST regression suite: 9 passed, 0 failed.
- Optimizer regression suite: 79 passed, 0 failed.
- `Generate` Stage-2 regeneration and Cargo build: exit 0, 18.75 s elapsed,
  881,536 KiB maximum RSS.
- `Generate_Binary_Nat` Stage-2 regeneration and Cargo build: exit 0,
  18.71 s elapsed, 820,888 KiB maximum RSS.

Before the change, Clippy reported seven Stage-2 `double_parens`
diagnostics: six in `Generate` and one in `Generate_Binary_Nat`.  Five were
parenthesized single-constructor matches that the match cleanup had replaced
with blocks while preserving the enclosing `Parenthesized` node:

| Variant | Stage-2 function | Previous location and shape |
| --- | --- | --- |
| `Generate` | `Omega_Words_Fun::conc` | `Omega_Words_Fun.rs:26`, `(*x)(({ ... }))` |
| `Generate` | `Omega_Words_Fun::build` | `Omega_Words_Fun.rs:63`, `(*w)(({ ... }))` |
| `Generate` | `Old_Datatype::push` | `Old_Datatype.rs:30`, `(*h)(({ ... }))` |
| `Generate` | `Extended_Nat::Minus::minus` | `Extended_Nat.rs:232`, `Enat::Enat(({ ... }))` |
| `Generate` | `Arith::case_nat` | `Arith.rs:791`, `(*g)(({ ... }))` |

The other two were the same `BigInt::term_ofa` expression in the two
variants.  Stage-1 contains `term_ofa((-i.clone()))`; M-LastUse removes the
last-use clone but deliberately preserves the surrounding syntax, leaving
`term_ofa((-i))` in the previous Stage-2 output.

The common cause was the call-argument printer.  A call already delimits each
argument, but `generate_call_argument` stripped an outer `Parenthesized` node
only when the argument was a cast.  It now strips outer parentheses for every
call argument at that local syntax boundary.  This is not a global
parenthesis cleanup: nested operator-precedence parentheses and callee
parentheses remain unchanged, and tuple expressions retain the parentheses
owned by their tuple node.  Regression tests cover block and unary arguments
and the tuple-preservation boundary.

After regeneration, Clippy with `-W clippy::all` exited 0 on both crates and
reported no `double_parens`: `7 -> 0`.  The complete warning summaries were
588 for `Generate` and 591 for `Generate_Binary_Nat`.  The five block sites
now print as `callee({ ... })` and both unary sites as `term_ofa(-i)`.

One diagnostic-extraction attempt in a parallel audit used `jq`, which is not
installed, and exited 127 before producing a report.  It changed no source or
generated artifact.  The successful audit used Cargo's human diagnostics and
`rg`; all generation, build, test, and final Clippy commands above succeeded.

## 2026-07-18: Conservative nested-constructor match fusion

This optimizer-only change reused the persistent Stage-1 artifacts and
regenerated both HOL-Codegenerator Stage-2 stress variants.  The new
`match_cleanup` rule fuses an outer single-field constructor pattern with an
immediately nested constructor match only when both matches end in the exact
generated `_ => panic!("non-exhaustive match")` fallback.  The duplicate
inner fallback is then represented by the one remaining outer fallback.

- Experiment fingerprint:
  `92fff631646619e75be52eefdab054408076ae141989539db4f1911257ade549`
- Optimizer regression suite: 96 passed, 0 failed.
- Rust formatting check: passed.
- `Generate` Stage-2 regeneration and Cargo build: exit 0, 16.75 s elapsed,
  793,992 KiB maximum RSS.
- `Generate_Binary_Nat` Stage-2 regeneration and Cargo build: exit 0,
  16.56 s elapsed, 829,120 KiB maximum RSS.
- Clippy 0.1.94 with `clippy::all`: both commands exited 0.

A second verification regeneration had already been started before the
parallel record update above became visible.  It used the same fingerprint
and also passed: `Generate` took 18.28 s with 834,364 KiB maximum RSS, and
`Generate_Binary_Nat` took 17.40 s with 834,296 KiB maximum RSS.  This was a
duplicate verification run, not a new experimental configuration; the first
measurements above remain the primary timing record.

The rule fused five sites in each variant: `Set::the_elem` and
`Lattices_Big::{max,min,inf_fin,sup_fin}`.  The generated pattern is now, for
example, `Set::Set(List::Cons(x, p1a))`; the redundant `match p0` and its
duplicate panic fallback are gone.  `Set::the_elem` retains its subsequent
`match *p1a`, because that is not a direct match on the outer constructor's
binding.  Clippy therefore reports `collapsible_match: 10 -> 0` across the
two variants.  The previously eliminated `double_parens` also remains zero.

The safety checks deliberately reject fusion when the outer constructor has
multiple fields, either successful arm has a guard, the inner body still uses
the eliminated outer binding, the match is not the direct tail of the outer
arm, or the two fallbacks are not the exact generated panic.  Five regression
tests cover the successful fusion, distinct panic strings, a single-variant
outer enum whose fallback must be retained after fusion, an outer guard, and
continued use of the outer binding.

The complete unique-primary diagnostic counts in the regenerated HOL crates
were:

| Clippy/rustc diagnostic | `Generate` | `Generate_Binary_Nat` |
| --- | ---: | ---: |
| `match_single_binding` | 467 | 269 |
| `type_complexity` | 571 | 572 |
| `overly_complex_bool_expr` | 1 | 1 |
| `too_many_arguments` | 2 | 2 |
| `unconditional_recursion` | 8 | 8 |
| Total | 1,049 | 852 |

These full totals must not be attributed to nested-match fusion or copied
into the paper.  This checkout simultaneously contains other uncommitted
`match_cleanup`/Boolean-pipeline changes; in particular, its current
function-root-only single-binding policy reintroduces the
`match_single_binding` diagnostics shown above.  The isolated result supported
by this experiment is the targeted `collapsible_match` reduction from 10 to
zero.  A manifest-aligned Standard/Unit/FPP recount is required after those
other changes stabilize before updating RQ3 totals.

Two non-mutating command attempts failed during verification.  The first
targeted `cargo test` invocation supplied two filter arguments, which Cargo
rejects (exit 1); rerunning with one filter passed all three then-current
targeted tests.  The first `cargo fmt --check` found formatting differences
in the new code (exit 1); the differences were corrected with scoped edits,
and the final format check passed.  No generation, Cargo build, optimizer
test, or final Clippy command failed.

## 2026-07-18: Deterministic complex-type cleanup

This optimizer change reused the persistent Stage-1 HOL-Codegenerator crates;
Isabelle was not rerun.  The final implementation adds an end-of-pipeline
`complex_type_cleanup` pass.  It alpha-normalizes in-scope type parameters,
deduplicates complex types within each module, emits deterministic generic
type aliases, and rewrites structured type positions in signatures, closure
annotations, casts, local annotations, fields, variants, constants, and
associated items.  References retain their outer reference node, and types
containing `impl Fn` are excluded.

RustLightAST now represents generic parameters on `TypeAlias` and stores a
closure parameter's pattern separately from its optional structured type.
This removes the previous need for copy/borrow/mut analyses to recover closure
types from printed parameter strings.  Alias selection mirrors Clippy's
default type-complexity score and threshold, including the implicit HIR tuple
used for `Fn(...)` inputs, so types below the lint threshold are not aliased.

- Experiment fingerprint:
  `827f37d64edcdc0c3a5d4d4a3d05c141e8c942514ac48ea60f5e6de048bcc7a7`
- RustLightAST regression suite: 10 passed, 0 failed.
- Optimizer regression suite: 103 passed, 0 failed.
- Rust formatting checks: passed in both repositories.
- Final `Generate` Stage-2 regeneration and Cargo build: exit 0, 19.10 s
  elapsed, 847,328 KiB maximum RSS.
- Final `Generate_Binary_Nat` Stage-2 regeneration and Cargo build: exit 0,
  17.36 s elapsed, 832,920 KiB maximum RSS.
- Clippy 0.1.94 with `clippy::all`: both commands exited 0.

Final generated-code measurements are:

| Workload | Rust files | Physical lines | cloc Rust code | Generated aliases |
| --- | ---: | ---: | ---: | ---: |
| `Generate` | 197 | 53,573 | 47,792 | 672 |
| `Generate_Binary_Nat` | 198 | 52,597 | 46,867 | 676 |

The targeted Clippy result is:

| Workload | `type_complexity` before | `type_complexity` after | Reduction |
| --- | ---: | ---: | ---: |
| `Generate` | 571 | 4 | 99.3% |
| `Generate_Binary_Nat` | 572 | 4 | 99.3% |
| Aggregate | 1,143 | 8 | 99.3% |

All structured-AST occurrences selected by Clippy's score are removed.  The
four remaining diagnostics in each variant are deliberately retained because
the parser preserves their containing trait declarations as `Item::Raw`:
`Quickcheck_Exhaustive::{FullExhaustive,CheckAll,Exhaustive}` and
`Quickcheck_Random::Random`.  The final complete warning profile is identical
for both variants: four `type_complexity`, one
`overly_complex_bool_expr`, two `too_many_arguments`, and eight rustc
`unconditional_recursion` diagnostics, for 15 warnings total per crate.

Several intermediate attempts were not retained:

- The first broad callable rule compiled both crates and reduced
  `type_complexity` to 9, but generated 1,447 aliases in `Generate` and 1,461
  in `Generate_Binary_Nat`.  It was replaced to avoid unnecessary code
  expansion.
- An attempted Raw-trait rewrite plus a lower structural threshold passed its
  six targeted tests, but its regeneration was deliberately interrupted
  before completion and the code was reverted.  Raw traits remain outside the
  final pass to preserve the parser's existing conservative boundary.
- The first Clippy-score approximation omitted the implicit `Fn` input tuple.
  It generated 558 aliases and left 86 `type_complexity` diagnostics in
  `Generate`; this calibration artifact was discarded.  Adding the HIR tuple
  weight produced the final 672-alias, four-diagnostic result.
- During the closure-parameter migration, two regression assertions initially
  expected quote-style `x : T` spacing.  The generated code correctly printed
  canonical `x: T`; both assertions were updated, after which all tests passed.
- One read-only `rg` inventory command used paths relative to the repository
  root while running from `optimize/`, so those three lookups reported
  `No such file or directory`.  The chained formatting and test commands still
  ran successfully and changed no generated artifact.
- A final formatting check was first invoked as `cargo fmt --check` from the
  Isabelle2Rust repository root, which has no root `Cargo.toml`; Cargo exited
  with an error before formatting anything.  Repeating the check with
  `--manifest-path optimize/Cargo.toml` passed.
- A final `cargo clippy --all-targets -- -D warnings` passed for RustLightAST
  but failed for the optimizer on 17 existing style diagnostics spread across
  borrow, closure, match, and mut analyses (for example redundant closures,
  `unnecessary_map_or`, and `needless_late_init`).  It reported no diagnostic
  in `complex_type_cleanup.rs`.  This stricter optimizer-self lint run is not
  the generated-code experiment and no unrelated style cleanup was attempted.

## 2026-07-18: Manifest-aligned final RQ3 code-quality recount

This recount uses exactly the corpus reported in RQ1: the standard
HOL-Codegenerator `Generate` crate, 50 Unit crates, and 36 FPP crates, for 87
Stage-1/Stage-2 pairs covering 3,909 exported definitions.  The experiment
fingerprint was
`827f37d64edcdc0c3a5d4d4a3d05c141e8c942514ac48ea60f5e6de048bcc7a7`.
The Stage-1 artifacts were unchanged and Isabelle was not rerun.  All 86 Unit
and FPP Stage-2 crates were refreshed after the optimizer changes, and every
optimization and Cargo build passed.  The standard HOL Stage-2 crate is the
successful artifact recorded in the deterministic complex-type cleanup above.

Clippy 0.1.93 was run with `clippy::all` on all 174 manifests by
`python3 scripts/test-rust-metrics.py clippy --processes 4 --cargo-jobs 1`.
Every Clippy command passed.

| Clippy/rustc diagnostic | Stage-1 | Stage-2 | Reduction |
| --- | ---: | ---: | ---: |
| `clone_on_copy` | 561 | 0 | 100% |
| `collapsible_else_if` | 89 | 0 | 100% |
| `collapsible_match` | 165 | 0 | 100% |
| `double_parens` | 288 | 0 | 100% |
| `match_single_binding` | 218 | 0 | 100% |
| `needless_bool` | 2 | 0 | 100% |
| `nonminimal_bool` | 10 | 0 | 100% |
| `overly_complex_bool_expr` | 1 | 1 | 0% |
| `too_many_arguments` | 2 | 2 | 0% |
| `type_complexity` | 573 | 4 | 99.3% |
| `unconditional_recursion` | 9 | 9 | 0% |
| **Total** | **1,918** | **16** | **99.2%** |

The four residual `type_complexity` diagnostics are the raw higher-order trait
signatures documented above.  The nine `unconditional_recursion` diagnostics
comprise eight coinductive stream operations in HOL-Codegenerator and the
intentionally nonterminating `Recursion_Test::f1` FPP definition.  The single
Boolean-expression and two function-arity diagnostics preserve their
source-level equations or interfaces.

Across the same corpus, exact `.clone()` call sites fall from 23,687 to 5,778,
a 75.6% reduction.  For the standard HOL-Codegenerator crate, cloc Rust code
falls from 56,866 lines in Stage-1 to 47,792 in Stage-2, a 16.0% reduction;
both artifacts compile.  Read-only `cloc` recounting reproduced a combined
104,658 Rust code lines for these two artifacts.  No experiment command failed
in this final recount.

## 2026-07-17: 10 * 100000 sbpf test

(
set -euo pipefail

ROOT="$(pwd)"
LOG_DIR="/tmp/sbpf-10x100k-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"

for round in $(seq 1 10); do
  echo "Running round ${round}/10"

  make micro_sbpf_gen X=100000 \
    2>&1 | tee "$LOG_DIR/round-${round}-generate.log"

  CARGO_PROFILE_DEV_OPT_LEVEL=3 make micro_sbpf \
    2>&1 \
    | rg 'micro_sbpf summary|Passed:|Failed:|Overall:' \
    | tee "$LOG_DIR/round-${round}-ocaml-stage1.summary"

  SBPF_ROOT="$ROOT" \
  SBPF_EXEC_DIR="$ROOT/tests_sbpf/tests/exec_semantics" \
  SBPF_DATA_DIR="$ROOT/tests_sbpf/tests/data" \
  SBPF_EXPORT_DIR="$ROOT/tests_sbpf/theory/stage2/bpf_generator" \
  SBPF_STEP_JSON="$ROOT/tests_sbpf/tests/data/ocaml_in.json" \
  SBPF_STAGE=2 \
  CARGO_PROFILE_DEV_OPT_LEVEL=3 \
  python3 tests_sbpf/tests/exec_semantics/sbpf_rust/run_step_micro.py \
    2>&1 \
    | rg 'Summary|Passed:|Failed:' \
    | tee "$LOG_DIR/round-${round}-stage2.summary"
)cho "All ten rounds completed. Summaries: $LOG_DIR"
Running round 1/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.02s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 2/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.03s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 3/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.03s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 4/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.04s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 5/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.04s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 6/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.03s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 7/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.04s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 8/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.03s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 9/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.06s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
Running round 10/10
>>> [micro_sbpf] generator: generating 100000 random step cases into tests_sbpf/tests/data/ocaml_in.json
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.04s
     Running `target/debug/step_test 100000`
Successfully generated 100000 random test cases.
Passed: 100000
Failed: 0
Passed: 100000
Failed: 0 (of which 0 panicked)
micro_sbpf summary
  Overall: PASS
Summary (step micro test, Rust export):
Passed: 100000
Failed: 0 (of which 0 panicked)
All ten rounds completed. Summaries: /tmp/sbpf-10x100k-20260716-192300
