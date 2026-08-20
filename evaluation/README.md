# Evaluation

This directory contains the scripts, measurement harnesses, and accepted data
used to evaluate the paper. Test theories and case-study models remain under
`test/`, `tests_sbpf/`, and `tests_x64/` until the repository-wide layout
migration.

## Layout

- `scripts/`: experiment-specific producers, grouped by research question.
- `harness/`: code linked into or around measured implementations.
- `results/`: only the currently accepted paper-facing data.

Generated build trees and newly recorded timestamped runs are ignored. Complete
historical records are kept in the author-side `Isabelle2Rust-evaluation-history`
archive rather than the artifact.

## Producers

Run commands from the repository root:

```sh
python3 evaluation/scripts/rq1/run-stable-builds.py
python3 evaluation/scripts/rq3/run-clippy.py
python3 evaluation/scripts/rq3/run-sbpf.py
make x64-performance
```

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

The current accepted performance data originated from the SBPF run
`20260820-052719+0800` and the x64 run `x64-20260820-053412+0800`. Timestamps
and exact host details remain recorded in the corresponding environment files.
