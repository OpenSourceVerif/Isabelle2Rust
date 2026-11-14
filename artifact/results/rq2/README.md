# RQ2 final results

This directory contains the optimization results produced by the agent in this
repository: ten cases, six configurations, and their primary workloads. Rust-only and Full achieve geometric mean speedups
of 4.35 and 10.84 over Off under arbitrary precision, respectively.

- `summary.json`: aggregate results, limitations, and controller identities.
- `matrix.json`: selected primary-workload rows and measurement references.
- `timings.csv`, `speedups.csv`, `normalized-matrix.csv`: measured results.
- `optimization-cost.csv`, `source-transforms.json`: costs and source changes.
- `full-sources.json`, `rust-only-sources.json`: per-case frozen program origins.
- `case-selection*.json`, `selection-provenance.json`:
  case selection and its experimental scope.
- `timing-quality.csv`, `scope-reviews.json`: timing and review qualifications.

These publication records contain final results and their experimental design.
Original raw evidence remains local. Stable evidence identifiers replace local
batch paths; the root evidence index records available original file hashes.
`checksums.json` hashes these publication copies.

The reported matrix covers primary workloads only. Auxiliary-workload
measurements are incomplete. Per-run implementation identities, configurations
and selected-program references are retained in the provenance records.

References starting with `evidence/` identify local raw evidence via the
publication evidence index; they are not paths inside this checkout.

The cohort is targeted: categories and observed source-optimization outcomes
informed selection, with at least five source-optimized cases sought. It is not
an unbiased sample or a corpus-wide source-optimization success estimate.
