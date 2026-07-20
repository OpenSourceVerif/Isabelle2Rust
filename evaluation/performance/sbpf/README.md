# RQ3 SBPF performance experiment

Run the complete experiment from the repository root with:

```sh
python3 evaluation/performance/sbpf/run.py
```

The script generates the fixed 6,000-vector instruction corpus with seed
`5984326`, regenerates the fixed default OCaml export, and derives every Rust
configuration from Stage-1 exports that combine the Word adapter with the
hybrid Native Int/Nat adapter. It builds with stable Rust in release mode,
builds the OCaml baseline with `ocamlopt`, validates all seven implementations,
runs a one-traversal pilot, and then measures three round-robin process runs.

Runtime is measured inside each harness after JSON parsing and semantic input
conversion. The Case-study baseline also constructs executables, VMs, and
input state before the measurement region. Peak RSS is the whole-process
maximum reported by `/usr/bin/time -v`.

Rust allocation builds use the same counting global allocator. Successful
`alloc` and `alloc_zeroed` calls add `layout.size()`; a successful `realloc`
adds `new_size`; `dealloc` does not reduce the cumulative total. The counter is
reset immediately before the measured workload. OCaml uses the difference of
`Gc.allocated_bytes ()` around the same region. Allocation measurements run in
separate processes from runtime measurements.

Outputs are written to `evaluation/performance/results/<timestamp>/`, including
the environment, configuration and executable hashes, commands, correctness
logs, per-process stdout/stderr, `raw.csv`, and `summary.csv`.
