# Isabelle2Rust Agent

An agent for translating executable Isabelle/HOL specifications into Rust,
repairing generated programs, and checking their behavior against executable
reference implementations. Optional optimization compares Rust refinement with
proof-checked Isabelle source transformations followed by Rust refinement.

## Repository layout

Most of this project's implementation is in **`agent/`**. The repository is built
on Isabelle2Rust: its translator, optimizer, source corpora, build support and
reference build support are retained for code extraction and
reference comparisons. These inherited directories are dependencies of the agent
experiments, not additional agent implementations.

```text
agent/                         Agent implementation and tools
├── src/i2r_agent/              Translation, repair, validation and optimization
├── isabelle/                  Isabelle extraction and agent integration
├── prompts/                   Model instructions
├── references/                Runtime knowledge and semantic guidance
├── config/                    Agent defaults and configuration schemas
├── scripts/                   Measurement, reporting and evidence-audit tools
├── tests/                     Agent regression tests and fixtures
└── docs/                      Detailed agent protocols
artifact/                      Agent experiment inputs and outputs
├── config.json                Shared paper-experiment configuration
├── run-agent                  Unified experiment entry point
├── run-fpp, run-unit           Dataset-specific aliases
├── datasets/                  Fixed inputs, manifests and export projects
├── results/                   Versioned final paper records (single entry)
│   ├── rq1/                   Translation correctness and recovery
│   ├── rq2/                   Optimization and numeric representation
│   └── rq3/                   Cross-language performance
└── runs/                      Local raw runs and history; Git-ignored
translate/                     Inherited Isabelle2Rust translation backend
optimize/                      Inherited Isabelle2Rust Rust optimizer
test/                         Inherited source corpora and reference harnesses
scripts/                       Inherited build-support scripts
Makefile, ROOT                 Isabelle2Rust build and session definitions
rust-toolchain.toml            Pinned Rust toolchain
```

`agent/config/` supplies implementation defaults; `artifact/config.json` selects
the shared experiment settings. Machine overrides and credentials stay local.
Read [artifact/results/README.md](artifact/results/README.md) for this paper's
results. See [agent/README.md](agent/README.md) for implementation details.
Retained code may include integration
adaptations; “inherited” does not mean byte-identical to the upstream release.

## Requirements and installation

Use Linux or macOS with Python 3.11+, Isabelle2025, Rust 1.94.0, and OCaml
with `ocamlfind`, `zarith`, and `yojson`. The runner uses POSIX process groups
and file locks. Install the Rust `clippy` and `rustfmt` components. Reference
builds also require a native compiler, Make, pkg-config, GMP, and Jansson.

Provide the RustLightAST dependency alongside this checkout, or set
`RUSTLIGHTAST_ROOT` to its directory. The experiment dependency revision is
`1d25bd1ac5b406cfc08c4554ab9980ce5986db8f`.

Run all commands below from the repository root:

```sh
python3.12 -m venv agent/.venv
agent/.venv/bin/pip install -e 'agent[test]'
rustup toolchain install 1.94.0 --profile minimal
rustup component add clippy rustfmt --toolchain 1.94.0

export ISABELLE=/path/to/Isabelle2025/bin/isabelle
export CARGO=/path/to/cargo
export OCAMLFIND=/path/to/ocamlfind
export RUSTLIGHTAST_ROOT=/path/to/RustLightAST
```

Put the OCaml tools on `PATH`. FPP requires no AFP session; workloads importing
AFP theories additionally require the matching AFP release via `AFP_ROOT`.
Tool overrides may be placed in the ignored `artifact/local.json`.

Model generation uses the provider and model configured in `artifact/config.json`
(default: DeepSeek Flash). Supply `DEEPSEEK_API_KEY` through the environment.
Preparation and boundary checks make no model calls; generation and optimization
consume API requests. Do not place credentials in versioned files.

## Quick start: model-free preparation

```sh
artifact/run-agent --help
artifact/run-fpp --run artifact/runs/smoke prepare --case fpp-add
artifact/run-fpp --run artifact/runs/smoke boundary --case fpp-add
```

This checks one FPP task's source/export and reference boundary. It does not
establish acceptance of an agent-generated program. Use a separate, new run
directory for a complete experiment.

## Generate and validate Rust

```sh
artifact/run-agent --dataset fpp --run artifact/runs/fpp-new pipeline --workers 10
artifact/run-agent --dataset fpp --run artifact/runs/fpp-new report

artifact/run-agent --dataset unit --run artifact/runs/unit-new pipeline --workers 10
artifact/run-agent --dataset unit --run artifact/runs/unit-new report
```

FPP selects 313 runnable roots, with 11 explicit exclusions from 324 roots.
Unit selects 488 root/source contexts. Each task has a budget of 48 attempted
model requests and 4200 active seconds. Preparation runs sequentially while
admitted tasks execute with the configured worker limit. The default limit is
five workers; the commands above explicitly select ten.

To pause and continue an experiment:

```sh
artifact/run-agent --dataset fpp --run artifact/runs/fpp-new pause
artifact/run-agent --dataset fpp --run artifact/runs/fpp-new resume-pipeline
```

Pause drains active work. Resume requires the same frozen implementation,
configuration, inputs, and tools; it retains consumed budgets. Use a new run
for changed settings. Never resume or overwrite a completed paper experiment.

## Optimization and performance

The performance dataset supports `--paired-numerics` with `--off`, `--rust-only`,
or `--full`. Rust-only and Full start independently from the same validated Off
artifact. Full additionally checks source equivalence in Isabelle. Paired builds
share business code and use arbitrary-precision or checked integer runtimes.

See [performance commands and controls](artifact/datasets/performance/README.md)
and [the optimization protocol](agent/docs/performance-experiments.md).
Final measurements must be separate from optimization search measurements.

## Recorded results

| Dataset | Completed | Accepted | Failed |
| --- | ---: | ---: | ---: |
| FPP | 313 | 307 | 6 |
| Unit | 488 | 479 | 9 |

The [correctness summary](artifact/results/rq1/summary.json) records
counts, budgets, costs, failures, and reference coverage. Ten Unit requests have
unknown token usage; known token totals are lower bounds. Stage2 derives from
Stage1. Differential checks provide finite behavioral evidence, not a proof of
Rust equivalence. Single-reference cases are reported explicitly.

The [consolidated paper results](artifact/results/README.md) contain RQ1
correctness/recovery, RQ2 optimization, and RQ3 cross-language measurements.
RQ2 aggregates
frozen outputs from multiple run directories using the same controller identity.
See [datasets and result locations](artifact/README.md). Generated run directories
are ignored by Git and are not included automatically in a source clone.

## Tests

```sh
agent/.venv/bin/python -m pytest -q agent/tests
```

Some tests require configured external tools. Test outcomes should be reported
with the environment; do not interpret skipped tool-dependent tests as passes.
