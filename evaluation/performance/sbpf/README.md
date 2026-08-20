# RQ3 SBPF performance experiment

Run the complete experiment from the repository root with:

```sh
python3 evaluation/performance/sbpf/run.py
```

For the grouped Stage-2 component experiment, which does not need the
cross-language baselines, use:

```sh
python3 evaluation/performance/sbpf/run.py --rust-only
```

To rebuild and remeasure only the OCaml baseline while reusing an existing
complete result matrix, use:

```sh
python3 evaluation/performance/sbpf/run.py \
  --ocaml-only-from evaluation/performance/results/<timestamp>
```

The script generates the fixed 6,000-vector instruction corpus with seed
`5984326`, regenerates the fixed default OCaml export, and derives every Rust
configuration from Stage-1 exports that combine the WordU128 layer with the
Checked128 Int/Nat profile. It builds with stable Rust in release mode,
builds the OCaml baseline with `ocamlopt`, validates all seven implementations,
runs a one-traversal pilot, and then measures three round-robin process runs.
For newly measured generated and OCaml configurations, the pilot selects a
whole-suite repetition count targeting approximately five seconds per process.
The prepared Solana baseline retains the historical configuration: 20
`SBPF-program` suites and one `SBPF-instruction` suite per process. Reported
runtime is normalized to one suite. Allocation uses one deterministic suite
traversal.

Runtime is measured inside each harness after JSON parsing and semantic input
conversion. For the case-study baseline, the `Executable`, input memory, stack,
context, memory mapping, and `EbpfVm` are constructed before measurement. One
independent VM is prepared for every timed execution, and each VM is executed
once. The timed interval only calls `execute_program` or `execute_step` and
checks its result. Bytecode loading and assembly are therefore outside the
measured region, while the generated semantic entry materializes its semantic
machine state inside it. Peak RSS is the whole-process maximum reported by
`/usr/bin/time -v`.
OCaml runtime harnesses use `clock_gettime(CLOCK_MONOTONIC)` through a small C
stub and honor the pilot-selected whole-suite repetition count.

Rust allocation builds use the same counting global allocator. Successful
`alloc` and `alloc_zeroed` calls add `layout.size()`; a successful `realloc`
adds `new_size`; `dealloc` does not reduce the cumulative total. The counter is
reset immediately before the measured workload. OCaml uses the difference of
`Gc.allocated_bytes ()` around the same region. Allocation measurements run in
separate processes from runtime measurements. The case-study baseline counter
covers only allocation inside the prepared interpreter calls; VM construction
is excluded.

The generated-Rust matrix is a grouped leave-one-out ablation:

- `Stage-1`: the original Rust export, copied without running `cargo-opt` or
  the RustLightAST parser/printer;
- `Stage-2 minus Borrow`;
- `Stage-2 minus Last-Use`;
- `Stage-2 minus Closure`;
- `Stage-2 Full`.

The optimizer exposes Copy, Borrow, Mut, Last-Use, and Closure as independent
pass-level switches, but the paper-facing table ablates only Borrow, Last-Use,
and Closure. Copy, Mut, and the remaining structural cleanup transformations
are enabled in every formal Stage-2 configuration. `--diagnostic` explicitly
runs the additional minus-Copy and minus-Mut checks; these rows are excluded
from the default performance matrix.

Outputs are written to `evaluation/performance/results/<timestamp>/`, including
the environment, configuration and executable hashes, commands, correctness
logs, per-process stdout/stderr, `raw.csv`, `summary.csv`, and
`grouped_ablation.csv`.
