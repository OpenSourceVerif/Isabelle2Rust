# Chapter 6 experimental boundary

Each statistical object has an independent producer. There is intentionally no
Chapter 6 orchestration script.

| Statistic | Scope | Producer |
| --- | --- | --- |
| Implementation LOC | Stage-1, Stage-2, RustLight | `count-implementation-loc.py` |
| RQ1 corpus and definition selections | two HCT configurations, tracked 55-Unit and 36-FPP corpus | `count-rq1-corpus.py` |
| RQ1 compiler acceptance | the same 93 Stage-1/Stage-2 pairs | `../evaluation/code_generation_quality/run-rq1-stable-builds.py` |
| RQ1 generated LOC | the same 93 pairs, reported by suite and stage | `count-rq1-generated-loc.py` |
| RQ1 translation/optimization time | phase-only, three independent runs | **missing: requires phase instrumentation before rerun** |
| RQ2 SBPF program agreement | 146 official programs | existing `make macro_sbpf` workflow |
| RQ2 SBPF instruction agreement | 10 independent batches of 100,000 vectors | `run-sbpf-10x100k.sh` |
| RQ2 x64 agreement | 10 independent batches of 100,000 vectors | `run-x64-10x100k.sh`; currently Stage-1 only |
| RQ2 generated LOC | three pure generated workload crates, both stages separately | `count-rq2-generated-loc.py` |
| RQ3 Clippy diagnostics | HCT-standard + Unit + FPP + three case-study crates, both stages | existing `make clippy-all REBUILD=1` workflow |
| RQ3 clone sites | exactly the same 95-pair corpus as Clippy | `count-rq3-clone-sites.py` |
| RQ3 SBPF runtime/allocation/ablations | SBPF-program and SBPF-instruction | `../evaluation/performance/sbpf/run.py` |
| RQ3 x64 runtime/allocation/ablations | X64-stepper | existing `make x64-performance` workflow |
| RQ3 PreferOwned ablation | all three workloads | **missing: no current independent producer for the paper's 1.87x/4.78x claim** |

Machine and tool versions are experiment metadata, not evaluation outcomes.
Peak RSS is retained as diagnostic provenance but is not a Chapter 6 result.
Percentages, normalized costs, and speedups are derived from raw counts or the
three run-level observations; they are not collected as independent data.
The 116 SBPF opcodes describe the case-study model and are not an experimental
outcome. Original-system heap allocation is outside the comparable measurement
boundary and must be recorded as unavailable, not as zero or as a normalized
allocation ratio.

HCT uses `export_code _`. Its selection count must come from the
`HOL_STRESS_STATS` line produced inside the two HCT theories, supplied to
`count-rq1-corpus.py` via `--hct-log`. Counting the literal `_` as one export is
invalid.
