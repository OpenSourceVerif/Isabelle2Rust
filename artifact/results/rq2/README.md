# RQ2 final results

This directory consolidates the ten-case, six-configuration primary-workload
results used in the paper. Rust-only and Full achieve geometric mean speedups
of 4.35 and 10.84 over Off under arbitrary precision, respectively.

- `summary.json`: aggregate results, limitations, and controller identities.
- `matrix.json`: selected primary-workload rows and measurement references.
- `timings.csv`, `speedups.csv`, `normalized-matrix.csv`: measured results.
- `optimization-cost.csv`, `source-transforms.json`: costs and source changes.
- `full-sources.json`, `rust-only-sources.json`: per-case frozen program origins.
- `case-selection*.json`, `selection-provenance.json`, `retained-records.json`:
  selection and retained-record references.
- `timing-quality.csv`, `scope-reviews.json`: timing and review qualifications.

Historical runs remain under `artifact/runs/`; they have not been deleted or
rewritten. This directory contains publication copies with personal absolute
path prefixes removed. Relative references beginning `artifact/` resolve from
the repository root; `workspace/` references identify material outside it.
Original evidence hashes identify the original files, not these redacted copies.
`checksums.json` hashes the publication copies. The raw run directories are
Git-ignored and are not bundled by a source clone.

The reported matrix covers primary workloads only. Auxiliary-workload
measurements are incomplete. Multiple source runs share one frozen controller
identity; these results do not claim to be a fresh run of the current checkout.
