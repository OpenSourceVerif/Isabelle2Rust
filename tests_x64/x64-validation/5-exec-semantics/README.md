# x64 executable-semantics experiment

This directory contains both the established OCaml correctness runner and the
RQ3 performance framework for `x64_step_test`.

Run the complete seven-implementation experiment from the repository root:

```sh
make x64-performance
```

To rebuild and remeasure only the OCaml baseline while reusing an existing
complete result matrix, use:

```sh
python3 tests_x64/x64-validation/5-exec-semantics/run.py \
  --ocaml-only-from evaluation/performance/results/x64-<timestamp>
```

The experiment reuses `../0-data/step4.json`; it never regenerates or runs the
x64 encoder. The fixed paper corpus is the first 6,000 entries in that file.
All implementations consume the same materialized JSON and are checked against
the recorded native CPU outcome before measurement.

The five generated-Rust configurations use the WordU128 layer and Checked128
Int/Nat profile. They are `Stage-1`, `Stage-2 minus Borrow`, `Stage-2 minus Last-Use`,
`Stage-2 minus Closure`, and `Stage-2 Full`. `Stage-1` is copied directly from
the original Rust export and does not run through `cargo-opt` or the
RustLightAST parser/printer. The optimizer exposes Copy, Borrow, Mut, Last-Use,
and Closure as pass-level switches, while the paper-facing matrix ablates only
Borrow, Last-Use, and Closure. Copy, Mut, and the remaining structural cleanup
transformations stay enabled in every formal Stage-2 configuration.
`--diagnostic` explicitly runs the additional minus-Copy and minus-Mut checks.

The standalone BigInt bit-operation lowering implementation remains in the optimizer
library, but the current optimization and evaluation pipelines do not invoke
it. The remaining baselines are the fixed Isabelle OCaml export compiled with
`ocamlopt` 4.11.2 and the existing ptrace-based native x64 execution method.

Each benchmark process is pinned to logical CPU 0. Parsing, input conversion,
result observation, and comparisons are outside the timer. A one-traversal
pilot chooses a whole-suite repetition count targeting at least five seconds
per runtime process, and results are normalized to one 6,000-step traversal.
Heap allocation uses one deterministic traversal. Runtime and allocation use
separate processes, with three runs per table cell. Rust uses an instrumented
global allocator, OCaml uses `Gc.allocated_bytes`, and the native C
baseline uses linker-wrapped allocation functions. Each counter is reset
immediately before the core step loop.
The OCaml runtime harness uses `clock_gettime(CLOCK_MONOTONIC)` through a small
C stub.
The output directory is printed as `RESULT_DIR=...` and contains the complete
reproduction trail plus `summary.csv`, `grouped_ablation.csv`, `derived.csv`,
and `experiment-record.md`.
