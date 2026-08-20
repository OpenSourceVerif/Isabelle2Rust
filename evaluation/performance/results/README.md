# Paper-facing RQ3 performance results

This directory tracks only the performance data currently used by the paper:

- `20260820-052719+0800/`: SBPF program and instruction workloads.
- `x64-20260820-053412+0800/`: x64 single-step workload.

Both result bundles contain the final raw measurements, summaries, environment,
configuration and binary hashes, correctness logs, pilot logs, and per-run
records. Absolute paths in their command and environment records are historical
facts from the measurement host and have intentionally not been rewritten.

The final runs reuse unchanged rows measured earlier. The exact source records
needed to audit those rows are retained under `provenance/`:

- `sbpf-stage1-20260820-042501+0800/`
- `x64-stage1-20260820-044143+0800/`
- `legacy-paper-snapshot/` for the frozen OCaml and case-study baseline rows

Superseded complete run directories are retained in an author-side archive
outside the Git repository and are not part of the artifact.
