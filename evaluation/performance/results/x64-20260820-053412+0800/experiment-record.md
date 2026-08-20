# RQ3 x64-stepper experiment record

- Base Git commit: `527b1a63da4b95759eed22b1ece52344f2e9435f`
- Git worktree: dirty at measurement time; `environment.json` records the status, and the configuration and binary manifests record exact optimizer, generated-source, and executable SHA-256 hashes.
- Measurement CPU: `0`
- Fixed input: `/home/ljy/fm2026/Isabelle2Rust/tests_x64/x64-validation/5-exec-semantics/data/x64_step_6000.json`
- Input SHA-256: `5bdffbfa2d672adfef981506020f5e42724ef6ab699495528054031c8a5f664e`
- Corpus construction: first 6000 vectors in source order from source SHA-256 `e6bbe7607f9fa1209fad12128447580639f7751a0346a0700900ec63794098a8`.
- Correctness: the four regenerated Stage-2 implementations passed 6000/6000 vectors against the recorded native x64 observations; the unchanged Stage-1, OCaml, and native baseline rows retain their earlier correctness validation.
- Reuse: the unchanged Stage-1 rows were reused from `/home/ljy/fm2026/Isabelle2Rust/evaluation/performance/results/x64-20260820-044143+0800`, and the frozen OCaml and native baseline rows were reused from `/home/ljy/fm2026/Isabelle2Rust/test/eval/rq3-x64-raw.csv`; the four paper-facing Stage-2 configurations were regenerated and remeasured.
- Timing: JSON parsing, input conversion, observation, and per-case comparison are outside the timed region. A one-traversal pilot selects a whole-suite repetition count for each newly measured implementation targeting approximately 5 seconds per independent CPU-pinned runtime process. Full and minus Closure use the larger of their two pilot repetition counts and run adjacently with alternating order. Each ablation effect is the median of the three within-round minus-pass/Full ratios. Results are normalized to one 6,000-vector traversal.
- Runtime suite repetitions: {"Stage-2 Full": 549, "Stage-2 minus Borrow": 226, "Stage-2 minus Closure": 549, "Stage-2 minus Last-Use": 291}.
- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.
- Rust allocation uses the same cumulative allocation counter as the SBPF experiment. OCaml uses `Gc.allocated_bytes`. The native C baseline uses linker-wrapped allocation functions and resets its cumulative counter immediately before the prepared ptrace step loop.

## Paper-facing Stage-2 ablations

- Borrow: minus/Full ratios 1.362312998, 1.416948159, 1.409108183; median 1.409108183 (Full faster, Full speedup 29.033128%, Full wins 3/3).
- Last-Use: minus/Full ratios 1.667340302, 1.762823059, 1.956330146; median 1.762823059 (Full faster, Full speedup 43.272809%, Full wins 3/3).
- Closure: minus/Full ratios 0.998149872, 0.969948695, 0.970074451; median 0.970074451 (Stage-2 minus Closure faster, Full speedup -3.084871%, Full wins 0/3).

| Implementation | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | KiB/step | Steps/s | Speedup vs Stage-1 | Time / OCaml | Time / native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stage-1 | 0.034350315 | 0.034177837 | 0.033913954 | 0.034177837 | 9.818316406 | 175552.362 | 1.000000 | 0.054871 | 0.900528 |
| Stage-2 minus Borrow | 0.016241328 | 0.016405661 | 0.013170317 | 0.016241328 | 3.882019531 | 369427.919 | 2.104375 | 0.026075 | 0.427931 |
| Stage-2 minus Last-Use | 0.019877826 | 0.020410258 | 0.018284961 | 0.019877826 | 5.056404948 | 301843.874 | 1.719395 | 0.031913 | 0.523747 |
| Stage-2 minus Closure | 0.011899820 | 0.011230227 | 0.009066861 | 0.011230227 | 2.742649740 | 534272.370 | 3.043379 | 0.018030 | 0.295897 |
| Stage-2 Full | 0.011921877 | 0.011578166 | 0.009346562 | 0.011578166 | 2.742649740 | 518216.788 | 2.951921 | 0.018588 | 0.305065 |
| OCaml baseline | 0.622871049 | 0.613594685 | 0.625063633 | 0.622871049 | 491.115390625 | 9632.812 | 0.054871 | 1.000000 | 16.411588 |
| Native x64 baseline | 0.038297277 | 0.036242034 | 0.037953125 | 0.037953125 | 0.000000000 | 158089.749 | 0.900528 | 0.060933 | 1.000000 |

## Artifacts

- `environment.json`: host, toolchains, CPU affinity, source/fixed input hashes, and counter probe.
- `configurations.json`: optimization-pass matrix, source hashes, build settings, and executable hashes.
- `binaries.json`: exact executables and hashes.
- `raw.csv`: one row per formal measurement process.
- `summary.csv`: three measurements and median for each paper metric.
- `grouped_ablation.csv`: within-round minus-group/Full ratios and their medians.
- `derived.csv`: throughput and cross-baseline ratios.
- `commands.txt`, `correctness/`, `pilot/`, and `runs/`: full reproduction trail.

Host instruction counts remain TBD: perf_event_open failed with errno 13 (Permission denied), perf_event_paranoid=2.
