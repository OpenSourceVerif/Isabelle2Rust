# RQ3: cross-language performance

Ten cases compare Rust-only arbitrary with OCaml, Haskell, Go, and Rust-S2.

| Reference | Geometric mean speedup | Excluding Queue |
| --- | ---: | ---: |
| OCaml | 7.07 | 3.99 |
| Haskell | 13.10 | 6.98 |
| Go | 80.34 | 48.65 |
| Rust-S2 | 143.25 | 96.95 |

- `summary.json`, `geometric-means.csv`: aggregates, intervals and sensitivity.
- `timings.csv`, `speedups.csv`, `primary-speedups.csv`,
  `normalized-runtimes.csv`: per-case measured results.
- `timing-quality.csv`: timing qualifications.
- `experiment-seal.json`, `measurement-provenance.json`,
  `delivery-verification.json`: configuration and source measurement references.

Speedup is reference runtime divided by Rust-only runtime. Measurements cover
prepared-input kernels, excluding input preparation and output encoding.
Haskell forces complete results within the timed region. Queue is unusually
favorable; the sensitivity analysis excludes it. AVL is slower than OCaml and
Haskell, and the Heap/OCaml difference is inconclusive. Consult timing warnings
and confidence intervals before interpreting precise ratios.

Original runs remain under `artifact/runs/` and are not included in a source
clone. Local development paths are represented by stable evidence identifiers.
Source hashes identify original evidence; `checksums.json` identifies copies.

References starting with `evidence/` identify local raw evidence via the
publication evidence index; they are not paths inside this checkout.
