# Rust ↔ OCaml runtime cross-test (sBPF exported semantics)

This directory mirrors the OCaml validation in `../` (`test.ml` + `glue.ml`) for the
**Rust** code exported from the same Isabelle sBPF semantics (`bpf_generator.thy`).

The exported test functions are self-checking — they take the *expected* result and
return a `bool`:

- `bpf_interp_test(lp, lm, lc, v, fuel, res, is_ok) -> bool` (whole-program interpreter)
- `step_test(lp, lr, lm, lc, v, fuel, ipc, i, res) -> bool` (single instruction)

The OCaml path (`Interp_test.bpf_interp_test`) is the **known-correct reference**: it
already passes all 146 program cases in `../test.ml`. So feeding the Rust export the
*same inputs* with the *same expected values* and asserting `true` is a direct
cross-test — any Rust case that does not return `true` is a runtime divergence from
the OCaml reference.

## Files

- `gen_interp_json.py` — extracts the 146 interpreter cases from `../test.ml` into the
  shared `../../data/interp_in.json` (single source of truth = `test.ml`).
- `interp_main.rs` — harness copied over the `interp_test` export's `src/main.rs`.
  Reads `interp_in.json`, converts `i64 → Int` (mirroring `glue.ml`), calls
  `bpf_interp_test`, and tallies pass/fail. Panics in the exported code are caught and
  counted as failed cases (a panic is itself a divergence from the OCaml `bool`).
- `step_main.rs` — analogous harness over `step_test`, reading the OCaml-reference step
  vectors in `../../data/ocaml_in.json` (hex-string schema with `ipc`/`result_expected`).

The JSON path is passed via the `CROSS_JSON` env var so the harness is independent of
cargo's working directory.

## Running

```sh
# regenerate the shared interp JSON from test.ml (only needed if test.ml changes)
python3 tests_sbpf/tests/exec_semantics/rust/gen_interp_json.py

# run the cross-test against the existing export under
# tests_sbpf/theory/stage1/bpf_generator (add REBUILD=1 to regenerate via Isabelle)
make sbpf
```

`make sbpf` swaps the harness into the export crate, adds `serde`/`serde_json` to its
`Cargo.toml`, and `cargo run`s it. The first run resolves serde from crates.io (cached
afterwards).

## Current status

- **interp**: 138 / 146 pass. The 8 failures are all `callx` / exit-cap / recursion
  cases (`test_callx`, `test_callx_imm`, `test_far_jumps`, `test_err_exit_capped_1`,
  `test_err_exit_capped_2`, `test_tight_infinite_recursion_callx`,
  `test_err_reg_stack_depth`, `test_err_callx_unregistered`). Each panics at the
  exported `impl Zero for Int { fn zero() { panic!("unimplemented instance method:
  zero") } }` — the Rust backend emitted a stub instead of `Int::ZeroInta` for the
  `Zero` instance of `Int`. The OCaml reference handles all 146. This is a genuine
  `code_rust.ML` gap surfaced by the cross-test, not a harness issue.
- **step**: 96 / 100 pass over `ocaml_in.json`. The 4 failures are all signed-division
  instructions (`sdiv` / `sdiv64`), which panic in the exported code — a separate
  divergence from the interp `Zero for Int` gap. The step phase is wired as
  best-effort (non-fatal) because the `step_test` export has historically had compile
  issues; it currently builds and runs here.
