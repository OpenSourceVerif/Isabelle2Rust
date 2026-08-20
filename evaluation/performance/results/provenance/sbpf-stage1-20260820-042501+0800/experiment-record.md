# RQ3 SBPF experiment record

- Base Git commit: `527b1a63da4b95759eed22b1ece52344f2e9435f`
- Git worktree: dirty at measurement time; `environment.json` records the status, and the configuration and binary manifests record exact optimizer, generated-source, and executable SHA-256 hashes.
- Measurement CPU: `0`
- SBPF-program input SHA-256: `cafc40d84adc2cf4a66673fdba81e734029de8c67795dbae4c09933ca8da2662`
- SBPF-instruction input SHA-256: `bc8bdb416345c369ee0f53d2e896f132f50433919fbf14f258d1b2d2ef5072b2`
- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the WordU128 layer and Checked128 Int/Nat profile; the OCaml baseline uses the fixed default export of the same Isabelle/HOL semantics.
- Correctness: all five generated-Rust configurations passed 146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors.
- Each value below is from an independent pinned process. Generated and OCaml pilots select whole-suite repetition counts targeting approximately 5 seconds. The prepared Solana baseline retains its historical configuration of 20 SBPF-program suites and 1 SBPF-instruction suite per process; every VM is independently constructed before measurement and executed once. Full and minus Closure use the larger of their two pilot repetition counts and run adjacently with alternating order. Every ablation effect is the median of the three within-round minus-pass/Full ratios. Reused rows retain their recorded protocol. Each allocation round uses one complete suite. Runtime results are normalized per suite.
- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.

## Paper-facing Stage-2 ablations

- SBPF-program / Borrow: minus/Full ratios 10.048695659, 9.518198497, 9.720032638; median 9.720032638 (Full faster, Full speedup 89.711969%, Full wins 3/3).
- SBPF-program / Last-Use: minus/Full ratios 175.584481375, 173.567331608, 172.066630843; median 173.567331608 (Full faster, Full speedup 99.423855%, Full wins 3/3).
- SBPF-program / Closure: minus/Full ratios 1.020462750, 0.994354561, 1.002211612; median 1.002211612 (Full faster, Full speedup 0.220673%, Full wins 2/3).
- SBPF-instruction / Borrow: minus/Full ratios 1.879301828, 1.811681552, 1.777606337; median 1.811681552 (Full faster, Full speedup 44.802661%, Full wins 3/3).
- SBPF-instruction / Last-Use: minus/Full ratios 31.641017199, 30.201788150, 29.240340008; median 30.201788150 (Full faster, Full speedup 96.688938%, Full wins 3/3).
- SBPF-instruction / Closure: minus/Full ratios 1.029484795, 0.971623797, 0.964464068; median 0.971623797 (Stage-2 minus Closure faster, Full speedup -2.920493%, Full wins 1/3).

Host instructions are `TBD`. The direct `perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)` probe failed with errno 13 (`Permission denied`), `perf_event_paranoid=2`, and no compatible `perf` executable was installed. No estimate was substituted.

## SBPF-program

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 88.576708026 | 88.852323124 | 89.176530167 | 88.852323124 |
| Stage-2 minus Borrow | 0.144707307 | 0.140049107 | 0.141795875 | 0.141795875 |
| Stage-2 minus Last-Use | 2.528522936 | 2.553839343 | 2.510108699 | 2.528522936 |
| Stage-2 minus Closure | 0.014695282 | 0.014630759 | 0.014620267 | 0.014630759 |
| Stage-2 Full | 0.014400606 | 0.014713825 | 0.014588004 | 0.014588004 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 1569.281250000 | 1569.203125000 | 1569.160156250 | 1569.203125000 |
| Stage-2 minus Borrow | 5.281250000 | 5.234375000 | 5.343750000 | 5.281250000 |
| Stage-2 minus Last-Use | 1566.117187500 | 1566.089843750 | 1566.160156250 | 1566.117187500 |
| Stage-2 minus Closure | 5.027343750 | 5.027343750 | 4.902343750 | 5.027343750 |
| Stage-2 Full | 4.898437500 | 5.027343750 | 4.933593750 | 4.933593750 |

### Heap allocation (MiB/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 370.059423159 | 370.059423159 | 370.059423159 | 370.059423159 |
| Stage-2 minus Borrow | 0.895576268 | 0.895576268 | 0.895576268 | 0.895576268 |
| Stage-2 minus Last-Use | 8.357981329 | 8.357981329 | 8.357981329 | 8.357981329 |
| Stage-2 minus Closure | 0.131730798 | 0.131730798 | 0.131730798 | 0.131730798 |
| Stage-2 Full | 0.131730798 | 0.131730798 | 0.131730798 | 0.131730798 |

### Host instructions (instructions/case)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Last-Use | TBD | TBD | TBD | TBD |
| Stage-2 minus Closure | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |

## SBPF-instruction

### Median runtime (s)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 5.787787820 | 5.773615723 | 5.642238711 | 5.773615723 |
| Stage-2 minus Borrow | 0.162173436 | 0.161437318 | 0.159127085 | 0.161437318 |
| Stage-2 minus Last-Use | 2.730446170 | 2.691254251 | 2.617525587 | 2.691254251 |
| Stage-2 minus Closure | 0.088838889 | 0.086580525 | 0.086336526 | 0.086580525 |
| Stage-2 Full | 0.086294513 | 0.089109103 | 0.089517618 | 0.089109103 |

### Peak RSS (MiB)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 24.039062500 | 24.019531250 | 24.019531250 | 24.019531250 |
| Stage-2 minus Borrow | 23.855468750 | 23.996093750 | 23.996093750 | 23.996093750 |
| Stage-2 minus Last-Use | 23.882812500 | 24.007812500 | 24.007812500 | 24.007812500 |
| Stage-2 minus Closure | 23.929687500 | 23.917968750 | 23.929687500 | 23.929687500 |
| Stage-2 Full | 23.929687500 | 23.929687500 | 23.859375000 | 23.929687500 |

### Heap allocation (KiB/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | 963.613432292 | 963.613432292 | 963.613432292 | 963.613432292 |
| Stage-2 minus Borrow | 35.540489583 | 35.540489583 | 35.540489583 | 35.540489583 |
| Stage-2 minus Last-Use | 569.755135417 | 569.755135417 | 569.755135417 | 569.755135417 |
| Stage-2 minus Closure | 21.342750000 | 21.342750000 | 21.342750000 | 21.342750000 |
| Stage-2 Full | 21.342750000 | 21.342750000 | 21.342750000 | 21.342750000 |

### Host instructions (instructions/step)

| Implementation | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Stage-1 | TBD | TBD | TBD | TBD |
| Stage-2 minus Borrow | TBD | TBD | TBD | TBD |
| Stage-2 minus Last-Use | TBD | TBD | TBD | TBD |
| Stage-2 minus Closure | TBD | TBD | TBD | TBD |
| Stage-2 Full | TBD | TBD | TBD | TBD |

## Artifacts

- `environment.json`: host, toolchains, affinity, inputs, and counter probe.
- `configurations.json`: pass matrix, source hashes, build settings, and executable hashes.
- `raw.csv`: one row per formal measurement process.
- `summary.csv`: the three values and median for every table cell.
- `grouped_ablation.csv`: within-round minus-group/Full ratios and their medians.
- `commands.txt`: every actual preparation, build, validation, pilot, and measurement command.
- `correctness/`, `pilot/`, and `runs/`: per-process stdout, stderr, and `/usr/bin/time -v` output.
