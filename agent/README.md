# Agent implementation

This directory contains the agent implementation. Start with the repository
[README](../README.md) for installation and experiment commands.

| Path | Contents and role |
| --- | --- |
| `src/i2r_agent/` | Python implementation: source analysis, translation, repair, validation, optimization and experiment control |
| `src/i2r_agent/numeric_runtime/` | Rust numeric runtime used by paired arbitrary/checked generated programs |
| `isabelle/` | Isabelle theories and ML extraction/integration code |
| `prompts/` | Model instructions used during translation, testing, review and repair |
| `references/` | Runtime reference material for Rust generation and semantic adaptation |
| `config/` | Default agent settings and preprocessing schemas; `local.toml` is ignored |
| `scripts/` | Measurement, reporting and evidence-audit utilities; see [script guide](scripts/README.md) |
| `tests/` | Regression tests for agent behavior |
| `tests/fixtures/` | Fixed test inputs and reference examples |
| `docs/` | Detailed workflow documentation, including [performance experiments](docs/performance-experiments.md) |
| `pyproject.toml` | Python package, dependencies and command entry points |
| `.gitignore` | Local environment and cache exclusions |

`agent/config/` contains implementation defaults. The paper experiment selects
its shared settings in `../artifact/config.json`; dataset manifests and projects
are under `../artifact/datasets/`. Use `../artifact/run-agent` to launch experiments.
The runner orchestrates preparation, generation, repair, reference comparison,
and optional optimization. Isabelle2Rust's `../translate/` and `../optimize/`
provide reference translation/optimization tools; `../test/` provides source
corpora and reference harnesses.

Local `.venv/`, `cache/`, `__pycache__/` and `.pytest_cache/` are generated and
ignored. They are not source components. Raw experiment state is in the ignored
`../artifact/runs/`. Versioned final records are in `../artifact/results/`. Generated program outputs
remain in local raw runs; the implementation delivered here is the agent in `src/`.

## Shared experiment modules

All datasets use the same controller; `--dataset` selects their inputs.

| Module in `src/i2r_agent/` | Responsibility |
| --- | --- |
| `experiment_runner.py` | Shared CLI, scheduling, preparation, pause/resume and worker dispatch |
| `dataset_artifact.py` | Dataset manifests, configuration and mechanical preparation |
| `request_budget.py` | Cross-process model-request budget reservations |
| `preparation_import.py` | Validated reuse of mechanical preparation |
| `fpp_suites.py` | FPP-specific observation inputs |
| `fpp_expansion.py` | FPP-specific observation adapters |

FPP and Unit both enter through `artifact/run-agent`; `run-fpp` and `run-unit`
only select a dataset. Unit's input adapter is under `artifact/datasets/unit/`.
