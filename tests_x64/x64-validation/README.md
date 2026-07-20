# x64 validation

This directory cross-validates the Isabelle-exported x64 encoder and executable
semantics on randomly generated single-instruction test cases.  The fixed OCaml
exports are compared with raw Rust exports of the same HOL entry points, and
both semantic implementations are checked against real x64 CPU execution.

The workflow never regenerates the existing OCaml files.  Before either test
stage, `make x64-rust-export` builds the Rust-only generator theories and
compiles their untouched stage1 Cargo crates.  A failed raw export or raw Cargo
build stops the workflow before random data or CPU tests are run.

The Rust and OCaml Isabelle entry points are deliberately identical:

- encoder: `x64_encode`
- semantics: `x64_step_test`

No Isabelle wrapper converts either entry point to an integer list.  Correctness
parsing, JSON support, and observation code are installed only in copied crates
under `x64-validation/_build`; generated stage1 source is not modified.

## Stage 1: generate test data

Run from the Isabelle2Rust repository root:

```bash
make x64-gen
```

`make x64-gen` generates 10000 cases by default. To choose another size:

```bash
make x64-gen X64_COUNT=100000
```

This stage produces the shared input files under `0-data/`:

- `1-x64-ins-gen`: randomly generates x64 assembly instructions into `0-data/step1.in`.
- `2-exec-assembler`: uses the already exported OCaml x64 encoder to encode those instructions into `0-data/step2.in`.
- Rust encoder adapter: calls the raw Rust `x64_encode`, unwraps its generated
  HOL `option/list/word` result in test code, and compares every byte sequence
  with the fixed OCaml `step2.in` output.
- `3-x64-map-gen`: generates register, flag, and memory inputs, then writes `0-data/step3.json`.

`x64_gen` remains as a compatibility alias for `x64-gen`.

## Stage 2: run and compare

Run from the Isabelle2Rust repository root:

```bash
make x64-test
```

This stage consumes the files from `0-data/`:

- `4-x64-stepper-c`: executes each binary instruction on the real x64 CPU and records the resulting register/flag state in `0-data/step4.json`.
- `5-exec-semantics`: runs the Isabelle-exported OCaml x64 semantics on the same cases and compares the OCaml result with `step4.json`.
- Rust stepper adapter: calls the raw Rust `x64_step_test` and compares its
  observed state with the same `step4.json` CPU oracle.  Its observation glue
  is appended only to the `_build` module copy because the generated register
  and flag constructors are private.

`x64_test` remains as a compatibility alias for `x64-test`.

The OCaml runner prints each result.  The Rust runners print summaries and full
expected/actual state for mismatches.  Any exporter, compiler, or comparison
failure makes the target exit nonzero.

The comparison always checks `PC` and the 15 tracked general-purpose registers.
For cases marked `cond = true`, it also checks the condition-code bits. `cmov`
and `jcc` cases compare all tracked flags (`ZF`, `CF`, `PF`, `SF`, `OF`).
`cmp` and `test` cases compare the flags that are defined by the current
Isabelle model and skip `PF`, because the model currently writes `PF` as
`Vundef`. Memory-state comparison is not enabled yet.

To run both stages:

```bash
make x64
```

## Expected result

For the standard 10000-case run:

```text
Rust encoder cross-check: 10000 passed / 0 failed
Summary: 10000 passed / 0 failed
Rust semantics vs CPU: 10000 passed / 0 failed (0 panicked)
```

This means the OCaml and Rust encoders agree, and both executable semantic
exports agree with the real x64 CPU stepper for the batch.

## Export controls and caching

The raw export gate can be run independently:

```bash
make x64-rust-export REBUILD=1
```

`REBUILD=1` forces both Isabelle exports and the copied correctness adapters to
rebuild.  Without it, existing stage1 exports and adapter cache stamps are
reused.  Relevant overrides are `RUST_TOOLCHAIN`, `CARGO`,
`X64_ISABELLE_THREADS`, `X64_ISABELLE_TIMEOUT`, `X64_ISABELLE_MAX_HEAP`, and
`X64_ISABELLE_JAVA_HEAP`.  The conservative default memory limits protect WSL
while exporting the large x64 code graph.

`make clean` removes Rust stage1 exports, correctness copies, Cargo targets, and
temporary executables.  It preserves the fixed OCaml files and `0-data` test
vectors.

## Performance baseline

Performance experiments must time the unmodified generated calls to
`x64_encode` and `x64_step_test`.  Input parsing, JSON decoding, state
serialization, and correctness comparison are adapter costs and are excluded
from the raw semantic timing.  End-to-end timings should be reported as a
separate metric.

## Dependencies

The pipeline needs:

- Rust and Cargo for `1-x64-ins-gen` and `3-x64-map-gen`.
- OCaml 4.11.2 with `ocamlfind` and `yojson` for `5-exec-semantics`.
- A C compiler and Jansson development library for `4-x64-stepper-c`.
- Linux ptrace support. The C stepper uses `PTRACE_TRACEME` on its own child process.

Quick checks:

```bash
ocamlc -version
ocamlfind query yojson
pkg-config --libs jansson
```
