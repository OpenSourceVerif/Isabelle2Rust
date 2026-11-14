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
Raw runs contain generated programs, reference observations, validation receipts
and reports. They remain local under Git-ignored `runs/`. The publication records
are self-contained summaries, not a bundle of every generated program or raw
observation. Use a new run directory for a new experiment.

## Performance

See [the performance dataset](datasets/performance/README.md) for generation,
optimization and final-matrix commands, and [the detailed protocol](../agent/docs/performance-experiments.md)
for budgets and acceptance rules. Use fresh final measurements for reported
comparisons; search timings are not final measurements.

[Final results](results/README.md) provide the paper's measurements and evidence
identifiers. RQ2 reports ten primary workloads; auxiliary measurements are not
part of the reported matrix.

## Versioned publication records

See [results/README.md](results/README.md) for the RQ1, RQ2 and RQ3 final records.
`results/` is versionable; `runs/` remains Git-ignored.
