# Frozen final RQ3 results

This directory contains the accepted final RQ3 snapshot.  It freezes the
eta-reduction-free Stage-2 performance and Clippy results together with the
previously accepted Stage-1 and external baselines.  The performance table in
`TOSEM/latex/63rq3.tex` is synchronized with these values.

- `rq3-performance.csv` records the values and precision intended for the
  revised paper table.
- `rq3-performance-runs.csv` records the three selected runs and exact medians
  underlying those values.
- `rq3-stage2-ablation.csv` records the paired Borrow, Last-Use, and Closure
  ablation ratios from the final Stage-2 runs.
- `rq3-sbpf-raw.csv` and `rq3-x64-raw.csv` freeze the process-level source
  rows, including elapsed time, suite repetitions, input and executable hashes,
  peak RSS, and allocated bytes.
- `rq3-correctness.csv` records the pass/fail totals and hashes of the
  corresponding correctness output for all 18 workload/implementation pairs.
- `rq3-provenance.csv` maps each frozen source file to its originating
  experiment snapshot and records the relevant file hashes.
- `rq3-clippy-corpus.csv`, `rq3-clippy-diagnostics.csv`, and
  `rq3-clippy-summary.csv` freeze the tracked 92-crate Stage-2 corpus and all 16
  residual diagnostics.  The accompanying environment, commands, and record
  files make the Stage-2-only recount auditable without rerunning Stage-1.
- `verify.py` reconstructs every run-level value and median from the raw rows
  and checks them against the accepted CSVs.  Pass `--check-paper` to also
  verify the synchronized table in `63rq3.tex`.

Run the audit from the `Isabelle2Rust` repository root:

```sh
python3 test/eval/verify.py
```

Runtime is reported per complete suite: 146 cases for `SBPF-program`, 6,000
vectors for `SBPF-instruction`, and 6,000 steps for `x64-stepper`. Cumulative
heap allocation is reported per case, vector, or step, respectively.
Normalized values use full Stage-2 as 1, so larger values indicate higher cost.
Runtime pilots choose an integer number of complete suites, targeting
approximately five seconds where practical. A run is not invalid merely
because it cannot be close to that target without splitting a suite; for
example, one Stage-1 `SBPF-program` suite already takes about 80 seconds.
The historical Solana rows retain their recorded single-use-VM protocol:
20 independently prepared suites for `SBPF-program` and one for
`SBPF-instruction`, with each VM executed once. Every reported runtime is the
median of three independent, CPU-pinned processes and is normalized to one
complete suite.

For the SBPF workloads, Original system denotes the prepared Solana interpreter
core. For `x64-stepper`, it denotes the ptrace-based native validation oracle.
Original-system allocation is zero because the prepared execution regions
triggered no counted allocation. Construction of the prepared VM or native
process state is outside this measurement, so these zeroes are not end-to-end
allocation results.

The raw CSVs in this directory are self-contained review snapshots. The
provenance manifest additionally identifies the original result directories,
configuration/environment manifests, commands, and their SHA-256 hashes.
Later exploratory measurements must not replace these frozen files.
