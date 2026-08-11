# Code-generation quality experiments

## RQ1 stable compiler acceptance

`run-rq1-stable-builds.py` selects the frozen tracked corpus (two HCT
configurations, 55 Unit theories, and 36 FPP theories), rejects unstable
feature gates and non-stable nested toolchain files, and builds both generated
stages with Rust 1.94.0 stable while removing `RUSTC_BOOTSTRAP`:

```sh
python3 evaluation/code_generation_quality/run-rq1-stable-builds.py
```

## Final RQ3 Stage-2 Clippy audit

The current stable-only protocol checks both stages of the same tracked
92-crate corpus:

```sh
make clippy
```

With Rust 1.94.0, Clippy 0.1.94, and `RUSTC_BOOTSTRAP` unset, the 2026-08-11 audit
completed all 184 commands and reported 1,984 Stage-1 diagnostics and 16
Stage-2 diagnostics.

`rq3-stage2-clippy-final/` records the accepted final Clippy audit for RQ3.
It contains the tracked 92-crate Stage-2 corpus, source and manifest hashes,
all 16 residual diagnostics, the exact commands, and the toolchain and
worktree metadata.  Stage-1 was not executed for this audit; its accepted
baseline is reused.  Reproduce the Stage-2 audit with:

```sh
python3 evaluation/code_generation_quality/run-rq3-stage2-clippy.py
```

The runner selects tracked theories only.  Untracked development examples
under `test/unit/example` are deliberately outside the frozen RQ3 corpus.

### SBPF and X64 case-study extension

The frozen 92-crate result above is the test-suite component of the paper
result.  The larger generated Rust artifacts used by the semantic-validation
case studies are audited separately with the same stable-Clippy command and
the same complete Stage-2 optimizer:

```sh
make clippy-case-studies
```

This command checks the pure generated crates for the SBPF program interpreter,
the SBPF single-instruction stepper, and the X64 stepper.  Benchmark drivers and
validation glue are deliberately excluded.  The first audit exposed three
Stage-2 categories absent from the frozen test-suite result:
`private_interfaces` (204), `clippy::upper_case_acronyms` (65), and
`clippy::clone_on_copy` (10).  It also found 11 instances of the already-known
`clippy::too_many_arguments`, for 290 Stage-2 diagnostics in total.

The visibility warnings came from public generated functions exposing private
generated datatypes; the generator now gives all nominal generated types the
same public visibility.  The front-loaded package-wide Copy pass now infers
local types through conditionals, generated closure calls, and constructor
results before Borrow runs, including removal of redundant outer match clones.
B-Match analyzes the resulting direct matches with the same occurrence-local
rule used for non-Copy clone-marked matches, so no trailing Copy cleanup is
required.  With Rust
1.94.0 and Clippy 0.1.94, the fixed 2026-08-12 audit reported 4,005 Stage-1
diagnostics and 11 Stage-2 diagnostics.  All 11 residuals were
`clippy::too_many_arguments` (4, 5, and 2 for the three workloads,
respectively).  Combining this disjoint component with the frozen test-suite
audit gives the paper totals of 5,989 Stage-1 and 27 Stage-2 diagnostics, a
99.5% reduction.  Explicit `.clone()` sites fall from 31,088 to 6,198 across
the same combined corpus, an 80.1% reduction.

Pass `REBUILD=1` after changing the Isabelle Rust generator to refresh all three
exports before optimization:

```sh
make clippy-case-studies REBUILD=1
```

When all original HOL/Unit/FPP generated directories are present, aggregate
them with these three case-study crates by running `make clippy-all`.  The
lower-level metrics command also accepts `--scope test-suites`, `--scope
case-studies`, or `--scope all`; the default remains `test-suites` so `make
clippy` continues to reproduce the frozen test-suite component.

`Cross_Target_Smoke.thy` reuses four existing Unit/FPP theories and exports the
same definitions to SML, OCaml, Haskell, Scala, Go, and Rust. It is intended to
check the cross-target harness before scaling the experiment to the complete
common corpus.

The paper-level comparison uses:

- 67 rule-directed unit-test theories; and
- 36 FPP theories that contain executable `export_code` commands.

For every target, record code-export success separately from compiler
acceptance. A missing compiler must be reported as unavailable, not as a failed
generated program.

## Performance extension

Performance should be evaluated only on definitions with a common executable
driver and identical inputs. Suitable FPP workloads are:

- `Quicksort_Test.quicksort` and `MergeSort_Test.msort`, on fixed random integer
  lists at several sizes;
- balanced-tree insertion and membership, on a fixed insertion sequence and
  query set; and
- the IMP compiler, on generated source programs of increasing size.

Each driver should read or construct the same inputs, evaluate the complete
result, and print a checksum to prevent dead-code elimination. Report cold-start
time separately from steady-state execution time, especially for Scala/JVM.
After warm-up, use at least 30 measured runs and report the median and
interquartile range. Build every target with its normal optimized production
configuration and record peak resident memory in addition to elapsed time.

These measurements should remain separate from the code-generation completion
table: runtime performance depends on workload, compiler, runtime system, and
input size, whereas export/build completion measures backend coverage.
