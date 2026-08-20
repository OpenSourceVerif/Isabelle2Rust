# RQ3 SBPF experiment record

- Base Git commit: `527b1a63da4b95759eed22b1ece52344f2e9435f`
- Git worktree: dirty at measurement time; `environment.json` records the status, and the configuration and binary manifests record exact optimizer, generated-source, and executable SHA-256 hashes.
- Measurement CPU: `0`
- SBPF-program input SHA-256: `cafc40d84adc2cf4a66673fdba81e734029de8c67795dbae4c09933ca8da2662`
- SBPF-instruction input SHA-256: `bc8bdb416345c369ee0f53d2e896f132f50433919fbf14f258d1b2d2ef5072b2`
- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the WordU128 layer and Checked128 Int/Nat profile; the OCaml baseline uses the fixed default export of the same Isabelle/HOL semantics.
- Correctness: the four regenerated Stage-2 implementations passed 146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; the unchanged Stage-1 rows were reused from `/home/ljy/fm2026/Isabelle2Rust/evaluation/performance/results/20260820-042501+0800`, and the frozen OCaml and case-study baseline rows were reused from `/home/ljy/fm2026/Isabelle2Rust/test/eval/rq3-sbpf-raw.csv`.
- Each value below is from an independent pinned process. Generated and OCaml pilots select whole-suite repetition counts targeting approximately 5 seconds. The prepared Solana baseline retains its historical configuration of 20 SBPF-program suites and 1 SBPF-instruction suite per process; every VM is independently constructed before measurement and executed once. Full and minus Closure use the larger of their two pilot repetition counts and run adjacently with alternating order. Every ablation effect is the median of the three within-round minus-pass/Full ratios. Reused rows retain their recorded protocol. Each allocation round uses one complete suite. Runtime results are normalized per suite.
- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.

## Paper-facing Stage-2 ablations

- SBPF-program / Borrow: minus/Full ratios 11.777757908, 12.243820989, 12.133248128; median 12.133248128 (Full faster, Full speedup 91.758184%, Full wins 3/3).
- SBPF-program / Last-Use: minus/Full ratios 227.925565248, 215.959526438, 228.442793036; median 227.925565248 (Full faster, Full speedup 99.561260%, Full wins 3/3).
- SBPF-program / Closure: minus/Full ratios 0.976738686, 0.974019090, 1.038674378; median 0.976738686 (Stage-2 minus Closure faster, Full speedup -2.381529%, Full wins 1/3).
- SBPF-instruction / Borrow: minus/Full ratios 1.708519956, 1.805935416, 1.836177819; median 1.805935416 (Full faster, Full speedup 44.627034%, Full wins 3/3).
- SBPF-instruction / Last-Use: minus/Full ratios 28.494927297, 30.109125721, 31.514421755; median 30.109125721 (Full faster, Full speedup 96.678748%, Full wins 3/3).
- SBPF-instruction / Closure: minus/Full ratios 0.966879710, 0.979004056, 1.059937018; median 0.979004056 (Stage-2 minus Closure faster, Full speedup -2.144623%, Full wins 1/3).

Host instructions are `TBD`. The direct `perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)` probe failed with errno 13 (`Permission denied`), `perf_event_paranoid=2`, and no compatible `perf` executable was installed. No estimate was substituted.

## SBPF-program

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 88.576708026 | 88.852323124 | 89.176530167 | 88.852323124 |
| Stage-2 minus Borrow | 0.147398970 | 0.156369511 | 0.148219383 | 0.148219383 |
| Stage-2 minus Last-Use | 2.852494831 | 2.758083900 | 2.790650078 | 2.790650078 |
| Stage-2 minus Closure | 0.012223912 | 0.012439490 | 0.012688414 | 0.012439490 |
| Stage-2 Full | 0.012515028 | 0.012771300 | 0.012215969 | 0.012515028 |
| OCaml baseline | 0.151179306 | 0.147996489 | 0.160406845 | 0.151179306 |
| Case-study baseline | 0.000047628 | 0.000051748 | 0.000114484 | 0.000051748 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 1569.281250000 | 1569.203125000 | 1569.160156250 | 1569.203125000 |
| Stage-2 minus Borrow | 5.187500000 | 5.281250000 | 5.226562500 | 5.226562500 |
| Stage-2 minus Last-Use | 1566.074218750 | 1566.085937500 | 1566.132812500 | 1566.085937500 |
| Stage-2 minus Closure | 5.023437500 | 4.933593750 | 5.023437500 | 5.023437500 |
| Stage-2 Full | 4.984375000 | 5.023437500 | 4.839843750 | 4.984375000 |
| OCaml baseline | 9.531250000 | 9.621093750 | 9.496093750 | 9.531250000 |
| Case-study baseline | 25.371093750 | 25.355468750 | 25.398437500 | 25.371093750 |

### Heap allocation (MiB/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 370.059423159 | 370.059423159 | 370.059423159 | 370.059423159 |
| Stage-2 minus Borrow | 0.895576268 | 0.895576268 | 0.895576268 | 0.895576268 |
| Stage-2 minus Last-Use | 8.274862211 | 8.274862211 | 8.274862211 | 8.274862211 |
| Stage-2 minus Closure | 0.096717416 | 0.096717416 | 0.096717416 | 0.096717416 |
| Stage-2 Full | 0.096717416 | 0.096717416 | 0.096717416 | 0.096717416 |
| OCaml baseline | 2.539450084 | 2.539450084 | 2.539450084 | 2.539450084 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Last-Use | TBD | TBD | TBD | TBD |
| Stage-2 minus Closure | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## SBPF-instruction

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 5.787787820 | 5.773615723 | 5.642238711 | 5.773615723 |
| Stage-2 minus Borrow | 0.151694662 | 0.168276802 | 0.163570868 | 0.163570868 |
| Stage-2 minus Last-Use | 2.529984125 | 2.805563999 | 2.807375881 | 2.805563999 |
| Stage-2 minus Closure | 0.085846519 | 0.091223457 | 0.094421584 | 0.091223457 |
| Stage-2 Full | 0.088787176 | 0.093179856 | 0.089082259 | 0.089082259 |
| OCaml baseline | 1.101820765 | 1.188248437 | 1.121931595 | 1.121931595 |
| Case-study baseline | 0.002857294 | 0.002120514 | 0.003508093 | 0.002857294 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 24.039062500 | 24.019531250 | 24.019531250 | 24.019531250 |
| Stage-2 minus Borrow | 23.996093750 | 23.996093750 | 23.925781250 | 23.996093750 |
| Stage-2 minus Last-Use | 23.871093750 | 24.003906250 | 23.878906250 | 23.878906250 |
| Stage-2 minus Closure | 23.988281250 | 23.855468750 | 23.925781250 | 23.925781250 |
| Stage-2 Full | 23.851562500 | 23.925781250 | 23.988281250 | 23.925781250 |
| OCaml baseline | 38.562500000 | 38.617187500 | 38.562500000 | 38.562500000 |
| Case-study baseline | 59.484375000 | 59.472656250 | 59.398437500 | 59.472656250 |

### Heap allocation (KiB/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 963.613432292 | 963.613432292 | 963.613432292 | 963.613432292 |
| Stage-2 minus Borrow | 35.540489583 | 35.540489583 | 35.540489583 | 35.540489583 |
| Stage-2 minus Last-Use | 569.755135417 | 569.755135417 | 569.755135417 | 569.755135417 |
| Stage-2 minus Closure | 21.342750000 | 21.342750000 | 21.342750000 | 21.342750000 |
| Stage-2 Full | 21.342750000 | 21.342750000 | 21.342750000 | 21.342750000 |
| OCaml baseline | 295.356296875 | 295.356296875 | 295.356296875 | 295.356296875 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Last-Use | TBD | TBD | TBD | TBD |
| Stage-2 minus Closure | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## Artifacts

- `environment.json`: host, toolchains, affinity, inputs, and counter probe.
- `configurations.json`: pass matrix, source hashes, build settings, and executable hashes.
- `raw.csv`: one row per formal measurement process.
- `summary.csv`: the three values and median for every table cell.
- `grouped_ablation.csv`: within-round minus-group/Full ratios and their medians.
- `commands.txt`: every actual preparation, build, validation, pilot, and measurement command.
- `correctness/`, `pilot/`, and `runs/`: per-process stdout, stderr, and `/usr/bin/time -v` output.
