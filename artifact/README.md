# Agent datasets and results

Start with the [agent installation and usage guide](../README.md).
`run-agent --dataset fpp|unit|performance|performance-source` selects the dataset;
`run-fpp` and `run-unit` are convenience aliases.

## Inputs

| Dataset | Location | Scope |
| --- | --- | --- |
| FPP | `datasets/fpp/manifest.json`, `datasets/fpp/projects/` | 313 runnable roots; 11 explicit exclusions |
| Unit | `datasets/unit/manifest.json`, `datasets/unit/projects/` | 488 root/source contexts |
| Performance | `datasets/performance/manifest.json` | Paired numeric and optimization experiments |
| Performance source | `datasets/performance-source/manifest.json` | Source-transformation experiment inputs |

Manifests freeze roots, source closures, hashes, and observation inputs. Keep
source theories, export projects, configurations, and input vectors unchanged
for an experiment. `config.json` supplies the shared experiment settings;
`local.json` supplies ignored machine-specific overrides.

## Correctness results

The versioned [result summary](results/rq1/summary.json)
records FPP 307/313 and Unit 479/488 accepted tasks, including all failures.
Completed raw evidence is located at:

- `runs/fpp-formal-clean-20261113/`
- `runs/unit-formal-20261113-r2/`

Runs contain generated programs, reference observations, reports, and validation
receipts. These local directories are Git-ignored; a source clone alone does not
include them. Stored receipts can contain machine-specific paths and must not be
published without an anonymity and relocation check. A current rerun uses a new
run directory and does not overwrite the recorded result.

## Performance

See [the performance dataset](datasets/performance/README.md) for generation,
optimization and final-matrix commands, and [the detailed protocol](../agent/docs/performance-experiments.md)
for budgets and acceptance rules. Use fresh final measurements for reported
comparisons; search timings are not final measurements.

The [final results](results/README.md) contain the reported aggregates and
references to their measured inputs:

- RQ2: `runs/matrix-representative-ten-v4-primary-20261114/` (ten primary workloads).
- RQ3: `runs/rq3-rust-only-ten-bounded-heap-20261114/` (Rust-only arbitrary versus four reference backends).

The RQ2 matrix references frozen selected programs from multiple runs with one
controller identity. Its parent measurement records are necessary evidence.
Auxiliary workload measurements are incomplete and are not the reported result.

## Versioned publication records

See [results/README.md](results/README.md) for the RQ1, RQ2 and RQ3 final records.
`results/` is versionable; `runs/` remains Git-ignored.
