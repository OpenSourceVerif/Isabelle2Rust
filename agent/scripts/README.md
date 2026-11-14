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
