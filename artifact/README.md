# Isabelle2Rust FPP artifact

This artifact adds the Agent and a Dashu numeric profile to Isabelle2Rust main `a792fd464574bc8fd3274c282974403d779de92e`. Existing BigInt and Checked128 profiles, the optimizer and the original tests (including HCT) remain available. This Agent experiment selects only FPP.

The supported workflow is `source-translation`, configured by the `translation` section. `artifact/run-fpp`, `i2r-fpp`, and `isabelle2rust-agent` select the same FPP runner. Runtime advisory material lives under `agent/references/`; historical workflow launchers are not part of this artifact. Shared review and kernel-performance components remain available, while the correctness experiment keeps performance disabled.

The Agent analyzes source dependencies, generates and compiles Rust, validates source tests, then runs fixed/generated differential checks. Source pages retain exact constructor evidence in a reversible typed tree with shared type definitions; original paths, ordered fields and hashes are checked against the source AST. Unsupported tree shapes retain their raw evidence. Paging requires exact page IDs and retained reading notes, with explicit feedback for malformed requests and repeated unread-page sets. Expectation corrections preserve AST, expected-slot, source-citation, unchanged-input, obligation and test-strength checks; string and character contents are treated as data. The direct runner uses portable repository discovery and main-layout compatibility without historical runner chains or model checkpoints.

`fpp-manifest.json` defines **324 unique exported roots: 313 runnable tasks and 11 explicit exclusions**. Each task retains its full source closure and original fixed/generated inputs. Counts are roots, not theories or closure members. The 43 complete FPP theories are the existing `test/fpp/` files. Runtime projects reconstruct historically admitted administrative export relocation from hash-checked recipes; source definitions and proofs are preserved. No old candidate, generated test, model analysis or model checkpoint is imported. Preparation builds mechanical source/wrapper and reference artifacts against this checkout; an explicit, strictly validated preparation-only import can reuse compatible mechanical artifacts as described below.

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

# Full 313-root pipeline: prepare sequentially while admitted tasks run.
artifact/run-fpp --run artifact/runs/fpp-full pipeline --workers 10
artifact/run-fpp --run artifact/runs/fpp-full pause
artifact/run-fpp --run artifact/runs/fpp-full resume-pipeline
artifact/run-fpp --run artifact/runs/fpp-full report
```

`pipeline` holds one exclusive controller lease, runs one model-free preparation child and dispatches up to the frozen number of generation workers. Only atomically published admissions that pass seal/configuration/source/reference checks can run. Preparation and generation retain their original per-task time and request charges. Pause drains the current preparation and all active generation tasks; `resume-pipeline` validates the same release and existing admissions before clearing the pause. Systemic preparation failures stop new dispatch. Unprepared roots remain pending in the full denominator. The sequential `prepare` / `resume-prepare` / `run` / `resume` commands remain available.

`prepare` makes no model calls and admits exact input/reference suites. Preparation holds the same exclusive controller lock as model dispatch. `pause` drains the current preparation and prevents the next task; `resume-prepare` validates the unchanged release/configuration before clearing the pause and continuing. A failed task receives a retained mechanical failure outcome and stays in the 313 denominator. Systemic preparation failures pause dispatch; later preparation skips already recorded failures and continues remaining tasks. It does not silently overwrite an old failure or claim that task was admitted. Completed model failures are never restarted or replaced by a successful retry. A new experiment requires a new run directory.

`run` and `pipeline` use DeepSeek Flash with the concurrency frozen by the first `prepare` or `pipeline --workers N` (default **5**, explicitly **10** above). Later commands, including resume and child workers, inherit that value; an explicit different value is rejected. Mechanical preparation remains sequential. Each task has **48 attempted requests and 4200 active seconds**, including charged preparation and previous transport segments. The global reservation ceiling is the sum of the per-task limits. Requests reserve a slot atomically before network submission; a crash does not refund a reservation. A controller lock inherited by children prevents overlapping controllers. Pause stops new dispatch and drains active tasks. Resume retains the same release/configuration identity, request ledger, model state and prior costs. Transport continuation archives previous outcomes and restores only the transport control penalty; repeated transport errors pause for investigation. Unreconciled crashed worker markers stop automatic restart.

A paused preparation-only run may adopt this scheduler revision through `migrate-pipeline --from-identity OLD_FROZEN_SHA256`, after its old controller has exited. This explicit migration requires zero model reservations, no generation artifacts, identical selection/configurations/tool sources/budgets, and changes limited to the runner and this README. It preserves byte-exact old release and budget snapshots, validates every existing admission, records the new release identity, and retains the original source/reference hashes and preparation seconds. It makes no model calls and leaves the pause in place; use `resume-pipeline` afterward. Once generation has started, release changes remain forbidden.

A fresh run can reuse compatible mechanical preparation from a paused, drained run without re-exporting. Historical runs with former workflow/configuration names or a different reference recipe are rejected by the strict importer; this cleanup does not migrate their configuration, checkpoints or reference identities:

```sh
artifact/run-fpp --run artifact/runs/fpp-new import-preparation --workers 10 \
  --from-run artifact/runs/fpp-old --from-identity OLD_FROZEN_SHA256
artifact/run-fpp --run artifact/runs/fpp-new pipeline
```

`import-preparation` checks the old release, every admitted source/project/wrapper/reference/input/tool/numeric identity, and all unchanged preparation recipes. Its reviewed revision boundary covers source-test resource and compiler repair, source-bound primitive contracts, entry-focused author responsibilities and their runner support; extraction, numeric configuration and reference recipes must still match exactly. Only the new run's heap and optimizer-target directories are rebound; old cache project paths and baseline identities remain exact read-only references, verified again in each generation child. Keep the origin directory available and unchanged. Original preparation seconds remain charged conservatively, and old model cost is archived separately; no old model outcomes or state enter the fresh run. Unprepared tasks are prepared normally by the pipeline. Import itself makes zero model calls and requires an empty target model ledger.

The frozen workflow repairs source tests first, runs differential acceptance afterward, and calls an independent source checker only on actual semantic source-test failure. Generation output limit is 32768; the source-checker override remains 65536. Performance review, measurement, optimization and a separate final-test phase are disabled by correctness-only configuration. Inputs/expected outputs are never changed to fit a candidate.

Source-test authors focus on entry behavior, meaningful business branches and semantic boundaries. Exact adopted Nat representation/zero/Suc/addition primitives are dependency context in arbitrary mode, with representative feasible large-data cases rather than separate helper suites; checked overflow and generic/non-Clone responsibilities remain. A source/type/mode-bound native addition contract is shared by generation, repair and independent source checking: its unary source equations do not require value-proportional execution, while business recurrence remains unchanged. Source-test authors distinguish large data from parameters controlling recursion, iteration, enumeration or output size. Unbounded arithmetic does not require infeasible execution or enormous outputs for every algorithm. Resource failures remain failures: exact runtime test names or at most four five-second exact-test isolation attempts establish scope, without inferring semantic correctness. Only an independent source judgment of infeasibility can authorize one resource resampling per suite lineage. This separate route changes numeric literal leaves in the exact affected test functions, keeps calls/assertion structure/test identities and source obligations, archives the original failure and test suite, and requires fresh independent review of all changed input/expected pairs followed by complete source and differential execution. Unsupported changes, unknown crash scope and insufficient source evidence stop unresolved. Ordinary expectation-repair guards are unchanged; all additional requests and diagnostic time consume the existing task budgets.

Correctness uses `arbitrary` arithmetic: mathematical `nat` is Dashu `UBig`, and `int`/`integer` are `IBig`, with `dashu-int =0.6.2`. Both Rust reference stages use the same library. Source subtraction, division by zero, signed floor division and numeric conversions retain Isabelle semantics. The locked FPP observations remain unchanged; separate numeric checks include values above 128 bits. Unbounded representation does not mean these finite observations exhaust the mathematical input domain. A future performance experiment should select a separate Checked128 configuration and its bounded input contract; this run does not measure performance.

For direct Stage1 use, import the new profile and keep the normal export command:

```isabelle
theory Example imports "Rust.Rust_Dashu_Setup" begin
definition increment :: "nat => nat" where "increment n = n + 1"
export_code increment in Rust module_name Example
end
```

The exported Cargo crate declares the pinned Dashu dependency. Pass that crate to the existing Stage2 optimizer; Stage2 consumes the Dashu Stage1 code directly, without renaming BigInt types after export.

`report.json` contains accepted/completed and accepted/all-root rates, failures, attempted calls, known tokens and unknown usage. The first-complete automatic rate is emitted only after all selected tasks finish; built-in model repairs count, later human framework repairs do not. The target is at least 95% of all 313 roots. A lower result is reported without an automatic framework iteration.

## Verification and limitations

With the configured OCaml bin directory on `PATH`, run the offline suite:

```sh
agent/.venv/bin/python -m pytest -q agent/tests
```

The current complete run reports **536 passed, 24 failed, 2 skipped and 97 passed subtests**; the suite is **not all green**. The same 24 tests were rerun against the complete pre-cleanup Git HEAD (`d8afbd9`) source and assets: all 24 failed with matching normalized error signatures. These existing failures remain visible and were not repaired as part of cleanup. The comparison uses a complete asset snapshot; an earlier incomplete in-memory baseline attempt was invalidated. Detailed comparison evidence is retained under ignored `artifact/runs/engineering/runtime-cleanup-r1/`.

Focused regressions cover protected expectation edits, primitive adaptation, source-test compilation repair and runner controls. Differential checks provide finite behavioral evidence, not a proof of Rust equivalence. Source/input/wrapper provenance remains in the manifest. Machine-specific tool paths and generated artifacts are intentionally ignored by Git.

## Reference adaptation

The reference layer retains bounded, source-bound adaptations for supported compiler failures and numeric primitive instances. These include BigInt dictionary/stub adaptation and compiler-located parenthesization of an `if` expression used as an addition operand. Natural subtraction saturates at zero, signed subtraction retains integer semantics, and ambiguous numeric instantiations are rejected. Existing generated methods are preserved. Failed builds and adaptation receipts remain available before recompiling Stage1 and reoptimizing Stage2; source theories, observation wrappers and input suites are unchanged. The focused regression is `agent/tests/test_reference_repairs.py`.

The current full-run selection is `fpp-manifest.json`. Historical selection manifests, including `reference-repair-r1.json`, remain as provenance and do not change that selection or combine previous model results with a fresh run. Use the full-run commands above and one frozen revision for all selected tasks.
