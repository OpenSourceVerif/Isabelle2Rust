# Evaluation Directory

- `scripts/`: evaluation producers grouped by research question.
  - `rq1/`: generated-code size and phase timing.
  - `rq2/`: differential validation and generated-code size.
  - `rq3/`: Clippy, runtime, heap-allocation, and ablation measurements.
- `harness/rq3/`: measurement adapters for the RQ3 workloads.
  - `common/`: shared native measurement support.
  - `sbpf/`: SBPF measurement harnesses.
  - `x64/`: x64 measurement harnesses.
- `results/`: result tables grouped by research question.
  - `rq1/`: compiler-acceptance, size, and timing summary.
  - `rq2/generated-loc.csv`: normalized generated-code size.
  - `rq2/sbpf/`: SBPF differential-validation results.
  - `rq2/x64/`: x64 differential-validation results.
  - `rq3/code-quality/`: Clippy summaries and the recorded environment.
  - `rq3/sbpf/`: SBPF runtime, heap-allocation, ablation, and environment records.
  - `rq3/x64/`: x64 runtime, heap-allocation, ablation, and environment records.

## Agent correctness experiments

- `results/agent/formal-20261113.json`: FPP and Unit final counts, costs, reference
  coverage, original release identities and evidence hashes.
- `scripts/agent/audit_formal.py`: read-only audit against the retained frozen
  releases and runtime receipts; no model calls.
- `../artifact/README.md`: shared launchers, datasets and raw run locations.
