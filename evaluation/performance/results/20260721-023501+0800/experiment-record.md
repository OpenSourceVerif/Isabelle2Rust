# RQ3 SBPF experiment record

- Git commit: `d444b290d44b28f123fab475c9f12b8222d59efb`
- Measurement CPU: `0`
- SBPF-program input SHA-256: `cafc40d84adc2cf4a66673fdba81e734029de8c67795dbae4c09933ca8da2662`
- SBPF-instruction input SHA-256: `bc8bdb416345c369ee0f53d2e896f132f50433919fbf14f258d1b2d2ef5072b2`
- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the Word adapter and hybrid Native Int/Nat adapter; the OCaml baseline uses the fixed default export of the same Isabelle/HOL semantics.
- Correctness: the four newly measured Stage-2 SBPF-instruction implementations passed 6000/6000 vectors; the unchanged SBPF-program, Stage-1, OCaml, and case-study rows were reused from `/home/ljy/fm2026/Isabelle2Rust/evaluation/performance/results/20260721-021806+0800`.
- Each value below is from an independent pinned process. For runtime, SBPF-program uses one traversal when it takes at least one second and exactly 20 traversals otherwise. The newly measured Stage-2 SBPF-instruction rows repeat the fixed 6000-vector suite 17 times (102,000 steps); unchanged baseline rows retain their recorded protocol. Heap allocation uses one complete suite because its byte count is deterministic. Runtime results are normalized per suite, and every metric is reported as the median of three process runs.

Host instructions are `TBD`. The direct `perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)` probe failed with errno 13 (`Permission denied`), `perf_event_paranoid=2`, and no compatible `perf` executable was installed. No estimate was substituted.

## SBPF-program

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 182.309157712 | 174.301450236 | 172.046699118 | 174.301450236 |
| Stage-2 minus Copy | 0.038668652 | 0.046347818 | 0.043119773 | 0.043119773 |
| Stage-2 minus Borrow | 0.127632348 | 0.136753287 | 0.124243814 | 0.127632348 |
| Stage-2 minus Mut | 3.034164395 | 3.174980864 | 2.917220025 | 3.034164395 |
| Stage-2 Full | 0.038927095 | 0.038809162 | 0.039519891 | 0.038927095 |
| OCaml baseline | 0.276332092 | 0.312345457 | 0.195636797 | 0.276332092 |
| Case-study baseline | 0.000047628 | 0.000051748 | 0.000114484 | 0.000051748 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 2087.097656250 | 2087.062500000 | 2087.062500000 | 2087.062500000 |
| Stage-2 minus Copy | 8.640625000 | 8.546875000 | 8.691406250 | 8.640625000 |
| Stage-2 minus Borrow | 6.039062500 | 6.125000000 | 6.093750000 | 6.093750000 |
| Stage-2 minus Mut | 2087.101562500 | 2087.082031250 | 2087.027343750 | 2087.082031250 |
| Stage-2 Full | 8.644531250 | 8.640625000 | 8.640625000 | 8.640625000 |
| OCaml baseline | 9.464843750 | 9.503906250 | 9.394531250 | 9.464843750 |
| Case-study baseline | 25.371093750 | 25.355468750 | 25.398437500 | 25.371093750 |

### Heap allocation (MiB/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 373.700626948 | 373.700626948 | 373.700626948 | 373.700626948 |
| Stage-2 minus Copy | 0.130889684 | 0.130889684 | 0.130889684 | 0.130889684 |
| Stage-2 minus Borrow | 0.845668322 | 0.845668322 | 0.845668322 | 0.845668322 |
| Stage-2 minus Mut | 11.833790087 | 11.833790087 | 11.833790087 | 11.833790087 |
| Stage-2 Full | 0.130889684 | 0.130889684 | 0.130889684 | 0.130889684 |
| OCaml baseline | 2.539449488 | 2.539449488 | 2.539449488 | 2.539449488 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Copy | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Mut | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## SBPF-instruction

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 13.175137303 | 11.327755512 | 14.976424056 | 13.175137303 |
| Stage-2 minus Copy | 0.074683833 | 0.076779390 | 0.075116189 | 0.075116189 |
| Stage-2 minus Borrow | 0.131877418 | 0.129595601 | 0.133095342 | 0.131877418 |
| Stage-2 minus Mut | 2.438952515 | 2.572483664 | 2.570239350 | 2.570239350 |
| Stage-2 Full | 0.066808736 | 0.074246955 | 0.075474168 | 0.074246955 |
| OCaml baseline | 0.924461126 | 2.677940845 | 2.480318069 | 2.480318069 |
| Case-study baseline | 0.002857294 | 0.002120514 | 0.003508093 | 0.002857294 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 24.546875000 | 24.558593750 | 24.570312500 | 24.558593750 |
| Stage-2 minus Copy | 24.582031250 | 24.640625000 | 24.652343750 | 24.640625000 |
| Stage-2 minus Borrow | 24.535156250 | 24.621093750 | 24.660156250 | 24.621093750 |
| Stage-2 minus Mut | 24.656250000 | 24.718750000 | 24.656250000 | 24.656250000 |
| Stage-2 Full | 24.589843750 | 24.714843750 | 24.589843750 | 24.589843750 |
| OCaml baseline | 38.617187500 | 38.773437500 | 38.542968750 | 38.617187500 |
| Case-study baseline | 59.484375000 | 59.472656250 | 59.398437500 | 59.472656250 |

### Heap allocation (KiB/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 1077.518020833 | 1077.518020833 | 1077.518020833 | 1077.518020833 |
| Stage-2 minus Copy | 17.351916667 | 17.351916667 | 17.351916667 | 17.351916667 |
| Stage-2 minus Borrow | 31.191869792 | 31.191869792 | 31.191869792 | 31.191869792 |
| Stage-2 minus Mut | 680.528278646 | 680.528278646 | 680.528278646 | 680.528278646 |
| Stage-2 Full | 17.351916667 | 17.351916667 | 17.351916667 | 17.351916667 |
| OCaml baseline | 295.356296875 | 295.356296875 | 295.356296875 | 295.356296875 |
| Case-study baseline | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000000 |

### Host instructions (instructions/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Copy | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Mut | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |
| OCaml baseline | TBD | TBD | TBD | TBD |
| Case-study baseline | TBD | TBD | TBD | TBD |

## Artifacts

- `environment.json`: host, toolchains, affinity, inputs, and counter probe.
- `configurations.json`: pass matrix, source hashes, build settings, and executable hashes.
- `raw.csv`: one row per formal measurement process.
- `summary.csv`: the three values and median for every table cell.
- `commands.txt`: every actual preparation, build, validation, pilot, and measurement command.
- `correctness/`, `pilot/`, and `runs/`: per-process stdout, stderr, and `/usr/bin/time -v` output.
