# Evaluation

This directory contains the scripts, measurement harnesses, and accepted data
used to evaluate the paper. Test theories and the SBPF and x64 case-study
models live under `test/`.

## Layout

- `scripts/`: shared producers, plus experiment-specific producers grouped by
  research question.
- `harness/rq3/`: measurement-only code linked into or around RQ3 workloads.
- `results/`: only the currently accepted paper-facing data.

Generated build trees and newly recorded timestamped runs are ignored. Complete
historical records are kept in the author-side `Isabelle2Rust-evaluation-history`
archive rather than the artifact.

## Producers

Run commands from the repository root:

```sh
python3 evaluation/scripts/count-implementation-loc.py
python3 evaluation/scripts/rq1/run-stable-builds.py
python3 evaluation/scripts/rq1/count-generated-loc.py
python3 evaluation/scripts/rq1/run-timings.py
evaluation/scripts/rq2/run-sbpf-10x100k.sh
evaluation/scripts/rq2/run-x64-10x100k.sh
python3 evaluation/scripts/rq2/count-generated-loc.py
python3 evaluation/scripts/rq3/run-clippy.py
python3 evaluation/scripts/rq3/count-clone-sites.py
python3 evaluation/scripts/rq3/run-sbpf.py
python3 evaluation/scripts/rq3/run-x64.py
```

The implementation LOC counter supports the architecture description and is
independent of the research questions. It counts the Stage-1 Isabelle/ML
backend and adapters, the Stage-2 Rust optimizer, and the separate RustLight
crate while excluding blank lines, comments, and test code.

The RQ1 generated-code counter considers only Rust library sources under each
generated crate's `src/` directory. It rejects test code, binary drivers,
benchmarks, examples, and build scripts; `cloc` excludes comments and blank
lines. The timing producer records Isabelle's `export_code` command time and
the release `cargo-opt` process time, excluding theory/proof checking and Cargo
compilation. Translation runs use one Isabelle worker so summed per-command
times are not distorted by concurrent exports. Isabelle does not emit command
timing below its built-in 1 ms relevance threshold; successful cases below
that threshold are recorded as zero and marked explicitly in `raw.csv`.
`evaluation/scripts/rq1/make-table.py` validates and combines the three
independent CSV outputs into the paper-facing rows; run it with `--help` for
the required input paths.

The harnesses used by the ordinary `macro_sbpf`, `micro_sbpf`,
`micro_sbpf_gen`, `x64`, `x64_gen`, and `x64_test` workflows are not part of
this directory. They remain with their SBPF and x64 test suites. Only the
additional adapters used by the RQ3 performance measurements are stored under
`harness/rq3/`.

The SBPF and x64 performance producers first write complete timestamped records
under `evaluation/results/rq3/`. After review, only the consolidated files used
by the paper are copied into the stable `sbpf/` and `x64/` directories.

## Accepted RQ3 results

`results/rq3/code-quality/` contains the frozen Stage-2 Clippy corpus, residual
diagnostics, summary, and toolchain environment.

`results/rq3/sbpf/` and `results/rq3/x64/` contain consolidated formal-process
measurements (`raw.csv`), paper-facing medians (`summary.csv`), grouped
leave-one-pass-out ratios (`ablation.csv`), and their measurement environments.
The x64 directory additionally contains derived throughput and cross-baseline
ratios in `derived.csv`.

In each `ablation.csv`, `median_minus_over_full` is the ratio of the median
runtime of the ablated configuration to the median runtime of full Stage-2.
The three `run_*_minus_over_full` columns retain the within-round ratios as
diagnostic measurements.

The current accepted performance data originated from the SBPF run
`20260820-052719+0800` and the x64 run `x64-20260820-053412+0800`. Timestamps
and exact host details remain recorded in the corresponding environment files.
