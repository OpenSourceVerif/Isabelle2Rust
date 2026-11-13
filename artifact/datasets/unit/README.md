# Unit dataset

This is the maintained input adapter for `test/unit`, used by the shared Agent
runner. It contains 488 root/source contexts across 54 theories (482 distinct
canonical names). Six Word roots occur under two source profiles and retain both
contexts and dependency closures.

- `manifest.json`: exact roots, closures, source hashes and fixed/generated inputs.
- `projects/`: algorithm export projects and HOL observation wrappers.
- `specs/`: wrapper specifications, grouped by authoring area.
- `root-catalog.json`: independently exported root/closure evidence.
- `build_manifest.py`: deterministic project/manifest reconstruction from these
  specifications and the existing catalog; no model calls. Run with Python 3.11+.

From the repository root, use `artifact/run-unit --run artifact/runs/unit-new
pipeline --workers 10` for a **new** experiment. Both datasets share generation,
repair, reference policy and budgets. Configure tools and credentials as described
in `artifact/README.md`. Never reuse the completed formal run directory.

The 2026-11-13 result is in `artifact/runs/unit-formal-20261113-r2/`; its
`final-snapshot/` is the historical release. The maintained manifest changes only
project locations relative to that release. Source/wrapper bytes, input vectors
and closure lists are retained. The shared config makes the original
`source_repair_then_diff_accept` policy explicit for both datasets.
