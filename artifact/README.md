# Isabelle2Rust FPP artifact

This artifact adds the Agent to Isabelle2Rust main `a792fd464574bc8fd3274c282974403d779de92e`. The original `translate/`, `optimize/`, and `test/` remain intact, including HCT. This Agent experiment selects only FPP.

The Agent analyzes source dependencies, generates and compiles Rust, validates source tests, then runs fixed/generated differential checks. Source pages retain exact constructor evidence in a reversible typed tree with shared type definitions; original paths, ordered fields and hashes are checked against the source AST. Unsupported tree shapes retain their raw evidence. Paging requires exact page IDs and retained reading notes, with explicit feedback for malformed requests and repeated unread-page sets. Expectation corrections preserve AST, expected-slot, source-citation, unchanged-input, obligation and test-strength checks; string and character contents are treated as data. The direct runner uses portable repository discovery and main-layout compatibility without historical runner chains or model checkpoints.

`fpp-manifest.json` defines **324 unique exported roots: 313 runnable tasks and 11 explicit exclusions**. Each task retains its full source closure and original fixed/generated inputs. Counts are roots, not theories or closure members. The 43 complete FPP theories are the existing `test/fpp/` files. Runtime projects reconstruct historically admitted administrative export relocation from hash-checked recipes; source definitions and proofs are preserved. No old candidate, generated test, model analysis or reference cache is imported. Preparation rebuilds mechanical source/wrapper and reference artifacts against this checkout.

## Installation

Use macOS or Linux with Python 3.11+, Isabelle2025, Rust/Cargo toolchain 1.94.0, OCaml with ocamlfind, and RustLightAST at commit `1d25bd1ac5b406cfc08c4554ab9980ce5986db8f`. `RUSTLIGHTAST_ROOT` may point to that clean checkout; by default it is the sibling `../RustLightAST`. Python dependencies are pinned in `agent/pyproject.toml`. The runner uses POSIX locks/process groups and is not Windows-compatible.

From this repository:

```sh
python3.12 -m venv agent/.venv
agent/.venv/bin/pip install -e 'agent[test]'
export ISABELLE=/path/to/Isabelle2025/bin/isabelle
export CARGO=/path/to/cargo
export OCAMLFIND=/path/to/ocamlfind
export RUSTLIGHTAST_ROOT=/path/to/RustLightAST
export DEEPSEEK_API_KEY=...  # supplied privately; never commit it
```

FPP requires no AFP session. `AFP_ROOT` is optional. Tool paths can also be supplied as a `tools` object in ignored `artifact/local.json`; model credentials should use the environment. All generated heaps, references, diagnostics, request/response archives, ledgers and reports belong to the selected ignored run directory. No Codex-managed Python runtime is required. Always keep the checkout and configured external tools unchanged once a run is prepared.

## Run

```sh
# Separate zero-model smoke run; never recycle this directory for the formal run.
artifact/run-fpp --run artifact/runs/smoke prepare --case fpp-add
artifact/run-fpp --run artifact/runs/smoke boundary --case fpp-add

# Full 313-root run, with fresh model work for every task.
artifact/run-fpp --run artifact/runs/fpp-full prepare
# If preparation was paused: explicit same-version continuation.
artifact/run-fpp --run artifact/runs/fpp-full resume-prepare
artifact/run-fpp --run artifact/runs/fpp-full run
artifact/run-fpp --run artifact/runs/fpp-full pause
artifact/run-fpp --run artifact/runs/fpp-full resume
artifact/run-fpp --run artifact/runs/fpp-full report
```

`prepare` makes no model calls and admits exact input/reference suites. Preparation holds the same exclusive controller lock as model dispatch. `pause` drains the current preparation and prevents the next task; `resume-prepare` validates the unchanged release/configuration before clearing the pause and continuing. A failed task receives a retained mechanical failure outcome and stays in the 313 denominator. Systemic preparation failures pause dispatch; later preparation skips already recorded failures and continues remaining tasks. It does not silently overwrite an old failure or claim that task was admitted. Completed model failures are never restarted or replaced by a successful retry. A new experiment requires a new run directory.

`run` uses DeepSeek Flash, at most **five concurrent task processes**, **48 attempted requests and 4200 active seconds per task**, including charged preparation and previous transport segments. The global reservation ceiling is the sum of the per-task limits. Requests reserve a slot atomically before network submission; a crash does not refund a reservation. A controller lock inherited by children prevents overlapping controllers. Pause stops new dispatch and drains active tasks. Resume retains the same release/configuration identity, request ledger, model state and prior costs. Transport continuation archives previous outcomes and restores only the transport control penalty; repeated transport errors pause for investigation. Unreconciled crashed worker markers stop automatic restart.

The frozen workflow repairs source tests first, runs differential acceptance afterward, and calls an independent source checker only on actual semantic source-test failure. Generation output limit is 32768; the source-checker override remains 65536. Performance review, measurement, optimization and a separate final-test phase are disabled by correctness-only configuration. Inputs/expected outputs are never changed to fit a candidate.

`report.json` contains accepted/completed and accepted/all-root rates, failures, attempted calls, known tokens and unknown usage. The first-complete automatic rate is emitted only after all selected tasks finish; built-in model repairs count, later human framework repairs do not. The target is at least 95% of all 313 roots. A lower result is reported without an automatic framework iteration.

## Verification and limitations

```sh
agent/.venv/bin/pytest -q agent/tests/test_expectation_literal_tokens.py agent/tests/test_fpp_controls.py
```

The Set0 archived full-proposal replay is engineering evidence, not a formal pass. The portable test includes the actual `revise` path and rejected open-expression controls. Differential checks provide finite behavioral evidence, not a proof of Rust equivalence. Input/wrapper provenance is retained in the manifest; the old experiments remain separate and paused. Machine-specific tool paths and generated artifacts are intentionally ignored by Git.

The migration checks pass (25 targeted tests, including cross-process budget limits, pause control, source workflow, repository discovery and Set0). The inherited offline suite is **not all green**: its first full run produced 380 passes, 26 failures and two historical-asset skips. All 25 non-environment failures also fail against an isolated byte-identical v45 core. One missing-OCaml-PATH failure passes with the configured OCaml bin on PATH. The historical repair-evidence existence check is now explicitly excluded, alongside the old non-FPP catalog and obsolete derived-worker CLI checks; this leaves 24 existing v45 workflow/fixture failures disclosed, not repaired or suppressed. Historical advisory evidence paths remain provenance metadata; the runtime does not open those archives. Local engineering comparison logs live under ignored `artifact/runs/engineering/`.

## Reference repair and fixed 48-task follow-up

`reference-repair-r1.json` fixes the follow-up selection to all 48 roots whose Rust references failed to compile in the original frozen run. This selection is independent of Agent success. The original 313-root first pass remains a separate result; the follow-up is not a best-of retry. Report both outcomes and their cumulative requests/tokens. Combining the follow-up with the untouched 265 results produces a batch with two reference revisions, not a uniformly rerun 313-root experiment.

The reference-only adapter runs once after a supported Stage1 compiler failure. It supplies generated BigInt class dictionaries for zero, one, addition and multiplication, replaces exact generated numeric panic stubs, and parenthesizes an `if` expression used as an addition operand. Subtraction requires an unambiguous Isabelle wrapper/root numeric instantiation: natural subtraction saturates at zero; integer subtraction stays signed. Ambiguous types are rejected. Real generated methods are preserved. The original failed build and the repair receipt are retained before recompiling Stage1 and reoptimizing Stage2. The source theories, observation wrappers, input suites, Agent implementation/prompts, and original translator/optimizer are unchanged by this reference recipe.

Mechanical validation compiled both stages for all 48 roots and executed 548 fixed plus 1920 generated observations under each of the ordinary and kernel protocols. Stage1, Stage2 and the existing OCaml reference agreed on all of these finite observations. The other 265 original roots compiled successfully and do not trigger the repair. The old 48 unavailability records are preserved; they concern this BigInt observation export, not the original direct-export benchmark configurations.

To reproduce the fixed follow-up with fresh model work, use a new run directory and the same environment setup above:

```sh
agent/.venv/bin/python - <<'PYTHON'
import json, subprocess
from pathlib import Path
ids=json.loads(Path('artifact/reference-repair-r1.json').read_text())['ids']
command=['artifact/run-fpp','--run','artifact/runs/fpp-reference-repair-r1','prepare']
for case in ids: command += ['--case',case]
subprocess.run(command,check=True)
PYTHON
artifact/run-fpp --run artifact/runs/fpp-reference-repair-r1 run
artifact/run-fpp --run artifact/runs/fpp-reference-repair-r1 report
```

Pause/resume commands are identical to the full-run commands. Use one frozen revision for every selected task; do not import previous model analysis, authored tests, candidates, or checkpoints. The original source/input manifests and DeepSeek Flash budget settings remain fixed. Local engineering compiler logs stay in ignored run directories. The focused adapter regression is `agent/tests/test_reference_repairs.py`.
