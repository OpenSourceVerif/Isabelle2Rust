# RQ3 x64-stepper experiment record

- Base Git commit: `527b1a63da4b95759eed22b1ece52344f2e9435f`
- Git worktree: dirty at measurement time; `environment.json` records the status, and the configuration and binary manifests record exact optimizer, generated-source, and executable SHA-256 hashes.
- Measurement CPU: `0`
- Fixed input: `/home/ljy/fm2026/Isabelle2Rust/tests_x64/x64-validation/5-exec-semantics/data/x64_step_6000.json`
- Input SHA-256: `5bdffbfa2d672adfef981506020f5e42724ef6ab699495528054031c8a5f664e`
- Corpus construction: first 6000 vectors in source order from source SHA-256 `e6bbe7607f9fa1209fad12128447580639f7751a0346a0700900ec63794098a8`.
- Correctness: all 5 measured implementations passed 6000/6000 vectors against the recorded native x64 observations.
- Reuse: no performance rows were reused.
- Timing: JSON parsing, input conversion, observation, and per-case comparison are outside the timed region. A one-traversal pilot selects a whole-suite repetition count for each newly measured implementation targeting approximately 5 seconds per independent CPU-pinned runtime process. Full and minus Closure use the larger of their two pilot repetition counts and run adjacently with alternating order. Each ablation effect is the median of the three within-round minus-pass/Full ratios. Results are normalized to one 6,000-vector traversal.
- Runtime suite repetitions: {"Stage-1": 143, "Stage-2 Full": 559, "Stage-2 minus Borrow": 308, "Stage-2 minus Closure": 559, "Stage-2 minus Last-Use": 237}.
- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.
- Rust allocation uses the same cumulative allocation counter as the SBPF experiment. OCaml uses `Gc.allocated_bytes`. The native C baseline uses linker-wrapped allocation functions and resets its cumulative counter immediately before the prepared ptrace step loop.

## Paper-facing Stage-2 ablations

- Borrow: minus/Full ratios 1.414947189, 1.455935156, 1.409566295; median 1.414947189 (Full faster, Full speedup 29.325984%, Full wins 3/3).
- Last-Use: minus/Full ratios 1.767813163, 1.774518840, 1.756649349; median 1.767813163 (Full faster, Full speedup 43.432936%, Full wins 3/3).
- Closure: minus/Full ratios 1.026590117, 0.990192408, 1.010135074; median 1.010135074 (Full faster, Full speedup 1.003338%, Full wins 2/3).

| Implementation | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | KiB/step | Steps/s | Speedup vs Stage-1 | Time / OCaml | Time / native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stage-1 | 0.034350315 | 0.034177837 | 0.033913954 | 0.034177837 | 9.818316406 | 175552.362 | 1.000000 | N/A | N/A |
| Stage-2 minus Borrow | 0.015349848 | 0.015658041 | 0.014887749 | 0.015349848 | 3.882019531 | 390883.349 | 2.226591 | N/A | N/A |
| Stage-2 minus Last-Use | 0.019177863 | 0.019084290 | 0.018553618 | 0.019084290 | 5.056404948 | 314394.719 | 1.790889 | N/A | N/A |
| Stage-2 minus Closure | 0.011136813 | 0.010649151 | 0.010668982 | 0.010668982 | 2.742649740 | 562377.929 | 3.203477 | N/A | N/A |
| Stage-2 Full | 0.010848354 | 0.010754628 | 0.010561936 | 0.010754628 | 2.742649740 | 557899.353 | 3.177966 | N/A | N/A |

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
