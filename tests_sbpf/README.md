# sBPF Validation

This directory contains the sBPF validation framework. It supports the
program-level macro test and the instruction-level micro step test.

## Macro Test Entry

Run from the Isabelle2Rust repository root:

```sh
make macro_sbpf
```

Useful options:

```sh
make macro_sbpf REBUILD=1          # regenerate Isabelle exports first
make macro_sbpf DATA_REBUILD=1     # refresh tests/data/interp_in.json
make macro_sbpf OCAML_REBUILD=1    # rebuild only the cached OCaml glue/binary
RUST_CASE_TIMEOUT=30 make macro_sbpf  # optional diagnostic timeout
```

## Micro Test Entry

Run the existing step-test data without regenerating it:

```sh
make micro_sbpf
```

Generate random step-test data without running the test:

```sh
make micro_sbpf_gen        # default: 100 cases
make micro_sbpf_gen X=250  # custom case count
```

## Macro Test Flow

`make macro_sbpf` calls `tests/exec_semantics/run_macro_sbpf.py`, which drives the
shared flow:

1. Ensure `theory/bpf_generator.thy` has exported both language versions.
   The relevant generated artifacts are:
   - `theory/stage1/bpf_generator/interp_test.ocaml`
   - `theory/stage1/bpf_generator/interp_test/`

2. Generate shared local macro data:
   - source: `tests/exec_semantics/sbpf_ocaml/test.ml`
   - output: `tests/data/interp_in.json`
   - cached by `tests/exec_semantics/_build/interp_in_cache.json`

3. Run the OCaml version:
   - runner: `tests/exec_semantics/sbpf_ocaml/run_interp_macro.py`
   - injects OCaml glue into the generated `interp_test.ocaml`
   - compiles it with `sbpf_ocaml/test.ml`
   - caches the compiled OCaml binary under `sbpf_ocaml/_build/`

4. Run the Rust version:
   - runner: `tests/exec_semantics/sbpf_rust/run_interp_macro.py`
   - installs `sbpf_rust/interp_main.rs` as the generated crate's `main.rs`
   - reads `tests/data/interp_in.json`
   - runs each macro case to completion by default and reports elapsed time
   - lists the slowest Rust cases at the end of the Rust summary
   - counts timeout only when `RUST_CASE_TIMEOUT` is explicitly set

The final output is a combined statistical summary for OCaml and Rust.

## Micro Test Flow

`make micro_sbpf` calls `tests/exec_semantics/run_micro_sbpf.py`, which drives
the shared instruction-level flow:

1. Ensure `theory/bpf_generator.thy` has exported both `step_test` language
   versions:
   - `theory/stage1/bpf_generator/step_test.ocaml`
   - `theory/stage1/bpf_generator/step_test/`

2. Read the shared step data from `tests/data/ocaml_in.json`.

3. Run the OCaml version:
   - runner: `tests/exec_semantics/sbpf_ocaml/run_step_micro.py`
   - injects integer-conversion glue into the generated `step_test.ocaml`
   - compiles it with `sbpf_ocaml/step.ml`

4. Run the Rust version:
   - runner: `tests/exec_semantics/sbpf_rust/run_step_micro.py`
   - installs `sbpf_rust/step_main.rs` as the generated crate's `main.rs`
   - reads `tests/data/ocaml_in.json`

`make micro_sbpf_gen` calls the local rbpf generator under
`tests/rbpf/step_test_random` and refreshes `tests/data/ocaml_in.json`.

## File Roles

- `tests/exec_semantics/run_macro_sbpf.py`: shared macro-test orchestration.
- `tests/exec_semantics/run_micro_sbpf.py`: shared micro-test orchestration and data generation entry.
- `tests/exec_semantics/gen_interp_json.py`: shared macro-data extraction.
- `tests/exec_semantics/sbpf_ocaml/`: OCaml-specific glue, local macro data, and runner.
- `tests/exec_semantics/sbpf_rust/`: Rust-specific glue harness and runner.
- `tests/rbpf/`: local copy of the Solana/rBPF test material.
- `tests/data/`: generated or stored validation data.

## Build Caching

Both the OCaml and Rust runners avoid redundant compilation across repeated runs
via a two-layer cache.

**Layer 1 — Isabelle export** (`ensure_isabelle_export` in `run_macro/micro_sbpf.py`):
checks whether the exported files under `theory/stage1/bpf_generator/` already
exist.  If so, `isabelle build` is skipped entirely.  Pass `REBUILD=1` to force
a re-export.

**Layer 2 — language build** (each runner script):
after the export step, each runner computes a SHA256 hash of the Isabelle-generated
source file (`Interp_test.rs` / `Step_test.rs` for Rust, the `.ocaml` export for
OCaml) together with the handwritten glue file (`interp_main.rs` / `step_main.rs`).
This key is compared against a stamp file written after the last successful compile.
If the key matches and the compiled binary still exists, the compile step is skipped.

Stamp file locations:

| runner | stamp |
|--------|-------|
| OCaml macro | `sbpf_ocaml/_build/macro_interp/.macro_interp_cache.json` |
| OCaml micro | `sbpf_ocaml/_build/micro_step/.micro_step_cache.json` |
| Rust macro  | `theory/stage1/bpf_generator/interp_test/.rust_macro_cache.json` |
| Rust micro  | `theory/stage1/bpf_generator/step_test/.rust_micro_cache.json` |

Rebuilds are triggered when: the Isabelle export produces different content,
the glue file is edited, the toolchain changes, or `REBUILD=1` is set.
