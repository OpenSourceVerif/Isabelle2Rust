# x64 executable-semantics correctness test

This directory contains the established OCaml correctness workflow used by
`make x64-test`, its `make x64_test` alias, and `make x64`:

- `x64_step_test.ml`: the fixed Isabelle/OCaml semantics export;
- `exec.ml`: the driver that compares the semantics with recorded native CPU
  observations.

The RQ3-only performance runner and its Rust, OCaml, and native measurement
adapters live under `evaluation/scripts/rq3/` and `evaluation/harness/rq3/x64/`.
