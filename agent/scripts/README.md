# Agent experiment tools

Run these Python tools from the repository root with `agent/.venv/bin/python`.
Generation and optimization use `artifact/run-agent`; these scripts provide
measurement, reporting and auditing around that workflow.

| Script | Purpose |
| --- | --- |
| `audit_formal.py` | Audit local frozen FPP/Unit evidence; writes an integration audit into the Unit run |
| `prepare_rq3_baselines.py` | Prepare cross-language reference baselines |
| `measure_rq3.py` | Check or measure the cross-language experiment |
| `report_rq3.py` | Render cross-language result reports |
| `report_rq2.py` | Render the optimization matrix and cost reports |
| `measure_source_first_stages.py` | Measure source-first stages |
| `measure_source_increment.py` | Measure source-change increments |
| `audit_performance_extremes.py` | Inspect extreme performance observations |

The frozen-evidence audit requires the original local runs and receipts; it is
not a source-clone smoke test. It makes no model calls. Final publication records
are in [artifact/results/](../../artifact/results/README.md); raw runs remain
local under `artifact/runs/`.

## RQ3 measurement configuration

The reported RQ3 comparison uses **Rust-only arbitrary**, primary workloads,
a maximum batch of 1024, and a maximum batch of 8 for leftist-heap merge.
Select these explicitly: `measure_rq3.py` defaults to Full and all workloads.
With a validated reference preflight directory and a completed RQ2 matrix
(including its canonical builds), check the inputs first:

```sh
agent/.venv/bin/python agent/scripts/measure_rq3.py \
  --preflight /absolute/rq3-preflight --matrix /absolute/matrix \
  --output /absolute/new/rq3-run --rust-mode rust-only --workloads primary \
  --max-batch 1024 --case-max-batch fpp-leftist-heap-merge=8 --action check
```

Run the same command with `--action measure` to collect fresh measurements.
The output directory must be separate from the preflight and matrix directories.
These inputs are local execution artifacts, not the publication summaries in
`artifact/results/`; measurement does not regenerate or repair candidate code.
