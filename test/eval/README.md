# Frozen RQ3 performance results

This directory contains the final paper-facing performance results for RQ3.
These values are frozen and are the only performance-result snapshot intended
for the review artifact.

- `rq3-performance.csv` reproduces the values and precision shown in the paper.
- `rq3-performance-runs.csv` records the three selected runs and exact medians
  underlying the paper-facing values.

Runtime is reported per complete suite: 146 cases for `SBPF-program`, 6,000
vectors for `SBPF-instruction`, and 6,000 steps for `x64-stepper`. Cumulative
heap allocation is reported per case, vector, or step, respectively.
Normalized values use full Stage-2 as 1, so larger values indicate higher cost.

For the SBPF workloads, Original system denotes the prepared Solana interpreter
core. For `x64-stepper`, it denotes the ptrace-based native validation oracle.
Original-system allocation is marked `NA` because its measurement scope is not
comparable with the generated semantics.

The exploratory process logs, build manifests, and intermediate result
directories under `evaluation/performance/results/` are intentionally excluded
from the review artifact. Do not replace the files in this directory with later
exploratory measurements.
