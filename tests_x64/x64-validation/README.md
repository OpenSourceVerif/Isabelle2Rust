# x64 validation

This directory validates the Isabelle-exported x64 executable semantics against
real x64 CPU execution on randomly generated single-instruction test cases.

The flow is split into two stages. It intentionally does not run Isabelle code
export, because the exported OCaml files are expensive to regenerate and are
expected to already exist under `tests_x64/theory/stage1/`.

## Stage 1: generate test data

Run from the Isabelle2Rust repository root:

```bash
make x64_gen
```

`make x64_gen` generates 10000 cases by default. To choose another size:

```bash
make x64_gen X64_COUNT=100000
```

This stage produces the shared input files under `0-data/`:

- `1-x64-ins-gen`: randomly generates x64 assembly instructions into `0-data/step1.in`.
- `2-exec-assembler`: uses the already exported OCaml x64 encoder to encode those instructions into `0-data/step2.in`.
- `3-x64-map-gen`: generates register, flag, and memory inputs, then writes `0-data/step3.json`.

If the OCaml exports under `tests_x64/theory/stage1/` are refreshed, update the
local runnable OCaml files in `2-exec-assembler/` and `5-exec-semantics/` before
running this target. This manual glue step does not invoke Isabelle.

## Stage 2: run and compare

Run from the Isabelle2Rust repository root:

```bash
make x64_test
```

This stage consumes the files from `0-data/`:

- `4-x64-stepper-c`: executes each binary instruction on the real x64 CPU and records the resulting register/flag state in `0-data/step4.json`.
- `5-exec-semantics`: runs the Isabelle-exported OCaml x64 semantics on the same cases and compares the OCaml result with `step4.json`.

Each successful case prints `true`. A mismatch prints `false` with expected and
actual values. The target exits with status 1 if any case fails.

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
Summary: 10000 passed / 0 failed
```

This means the executable OCaml semantics and the real x64 CPU stepper agree on
all generated cases in this batch.

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
