# RQ3 SBPF experiment record

- Git commit: `d444b290d44b28f123fab475c9f12b8222d59efb`
- Measurement CPU: `0`
- SBPF-program input SHA-256: `cafc40d84adc2cf4a66673fdba81e734029de8c67795dbae4c09933ca8da2662`
- SBPF-instruction input SHA-256: `bc8bdb416345c369ee0f53d2e896f132f50433919fbf14f258d1b2d2ef5072b2`
- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the Word adapter and hybrid Native Int/Nat adapter; the OCaml baseline uses the fixed default export of the same Isabelle/HOL semantics.
- Correctness: the four regenerated Stage-2 implementations passed 146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; the unchanged Stage-1, OCaml, and case-study baselines were reused from `/home/ljy/fm2026/Isabelle2Rust/evaluation/performance/results/20260721-005433+0800`.
- Each value below is from an independent pinned process; fast Stage-2 suites are batched according to a pilot to target at least five seconds per process, normalized per suite, and reported as the median of three process runs.

Host instructions are `TBD`. The direct `perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)` probe failed with errno 13 (`Permission denied`), `perf_event_paranoid=2`, and no compatible `perf` executable was installed. No estimate was substituted.

## Stage-2 strategy validation

- Implemented items 1--4: explicit and standard-library Copy facts, semantic Copy/Borrow decoupling with size-aware calling conventions, field-sensitive non-consuming pattern matching, and crate-wide call-graph propagation of Copy-specialization requirements.
- `cargo clippy -- -D clippy::clone_on_copy` succeeds for both regenerated Full workloads, leaving zero residual `clone_on_copy` diagnostics.
- Relative to the pre-change Full medians in `20260720-213206+0800`, the updated Full runtime is 30.68% lower for SBPF-program (0.057822841 s to 0.040084834 s) and 24.87% lower for SBPF-instruction (0.104202361 s to 0.078288783 s). Both exceed the 15% stopping threshold, so optional item 5 was not implemented or measured.
- Copy's marginal runtime effect is +4.85% for SBPF-program (minus Copy 0.042129870 s versus Full 0.040084834 s). For SBPF-instruction, the raw median differs by -0.61% (0.077810266 s versus 0.078288783 s), which is smaller than the observed three-run spread; the paper reports both as 0.078 s and does not claim an independent Copy speedup for that workload.
- Updated Full is 6.89x faster than the unchanged OCaml baseline for SBPF-program and 31.68x faster for SBPF-instruction.

## SBPF-program

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 182.309157712 | 174.301450236 | 172.046699118 | 174.301450236 |
| Stage-2 minus Copy | 0.043254225 | 0.039930800 | 0.042129870 | 0.042129870 |
| Stage-2 minus Borrow | 0.138871655 | 0.122332609 | 0.132339236 | 0.132339236 |
| Stage-2 minus Mut | 2.634481253 | 2.419133037 | 2.537606136 | 2.537606136 |
| Stage-2 Full | 0.043181027 | 0.040084834 | 0.040078658 | 0.040084834 |
| OCaml baseline | 0.276332092 | 0.312345457 | 0.195636797 | 0.276332092 |
| Case-study baseline | 0.000047628 | 0.000051748 | 0.000114484 | 0.000051748 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 2087.097656250 | 2087.062500000 | 2087.062500000 | 2087.062500000 |
| Stage-2 minus Copy | 8.851562500 | 8.718750000 | 8.863281250 | 8.851562500 |
| Stage-2 minus Borrow | 6.128906250 | 6.070312500 | 5.976562500 | 6.070312500 |
| Stage-2 minus Mut | 2087.113281250 | 2086.988281250 | 2087.078125000 | 2087.078125000 |
| Stage-2 Full | 8.839843750 | 8.875000000 | 8.859375000 | 8.859375000 |
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
| Stage-2 minus Copy | 0.077810266 | 0.079802032 | 0.074862725 | 0.077810266 |
| Stage-2 minus Borrow | 0.133013419 | 0.127421651 | 0.134856865 | 0.133013419 |
| Stage-2 minus Mut | 2.758312446 | 2.526933479 | 2.595396557 | 2.595396557 |
| Stage-2 Full | 0.078288783 | 0.078978467 | 0.076670507 | 0.078288783 |
| OCaml baseline | 0.924461126 | 2.677940845 | 2.480318069 | 2.480318069 |
| Case-study baseline | 0.002857294 | 0.002120514 | 0.003508093 | 0.002857294 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 24.546875000 | 24.558593750 | 24.570312500 | 24.558593750 |
| Stage-2 minus Copy | 24.652343750 | 24.527343750 | 24.714843750 | 24.652343750 |
| Stage-2 minus Borrow | 24.535156250 | 24.597656250 | 24.535156250 | 24.535156250 |
| Stage-2 minus Mut | 24.781250000 | 24.531250000 | 24.718750000 | 24.718750000 |
| Stage-2 Full | 24.761718750 | 24.589843750 | 24.757812500 | 24.757812500 |
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
