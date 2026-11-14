# Paired numeric experiment

This opt-in dataset contains ten cases selected before their numeric timing:
integer GCD, higher-order map, queue draining, merge sort, AVL insert **and**
delete, arithmetic-expression compilation, Eratosthenes, and polynomial
evaluation, HOL Fibonacci and leftist-heap merge.
`manifest.json` freezes source hashes, complete entry sets, ordinary
and kernel observations, workload sizes/shapes, and the primary plotting input.
No old generated Rust or exploratory measurements are imported as new results.

## Controls

The shared runner has two mutually exclusive flag groups:

- `--arbitrary`, `--checked`, `--paired-numerics`.
- `--off` (default), `--rust-only`, `--full`.

Omitting the numeric flag inherits the original configuration. With old
configuration and `--off`, no experiment file is created, no config field is
added, no numeric wrapper is introduced, and no performance stage is executed.
Old FPP/Unit datasets and frozen experiment outputs are unchanged.

`--paired-numerics --off` is a **new, explicit generation configuration**. It
generates and validates one implementation against `i2r_numeric::Nat/Int` under
arbitrary semantics. This configuration does not inherit the old experiment's
correctness evidence. It runs the original generation, source-testing, repair
and reference-acceptance stages for its new artifact.

`--rust-only` and `--full` append a separate performance stage after correctness
acceptance. They independently start from the same accepted off implementation.
The original acceptance lock and delivered crate are never edited. The search
branch reads the existing SPG, implementation guidance and source-to-Rust map;
each Rust transaction updates mapping and guidance through the shared APIs.
The selected deliverable is `optimization/<case>/output/`, with a separate
`selected-state.json`, validation record, complete proposal history and budget
ledger. Its path and file hashes appear in `optimization-report.json`; the
original correctness output remains the frozen off baseline.

```sh
artifact/run-agent --dataset performance --run /absolute/new/run \
  --paired-numerics --off pipeline
artifact/run-agent --dataset performance --run /absolute/new/run measure

# Reuse an accepted baseline without generating or reviewing its tests again.
artifact/run-agent --dataset performance --run /absolute/rust-run \
  --paired-numerics --rust-only optimize --from-run /absolute/new/run
artifact/run-agent --dataset performance --run /absolute/full-run \
  --paired-numerics --full optimize --from-run /absolute/new/run

# Fresh final measurements; search measurements are not the reported matrix.
agent/.venv/bin/python -m i2r_agent.optimization_matrix \
  --baseline /absolute/new/run --rust /absolute/rust-run \
  --full /absolute/full-run --output /absolute/matrix
```

Configure tool paths with the existing `ISABELLE`, `AFP_ROOT`, `CARGO` and
`OCAMLFIND` environment variables, and provide `DEEPSEEK_API_KEY` through the
existing credential mechanism. No credential is included in this artifact.
The initial generation retains the shared runner's 48-call/4200-active-second
per-case limits. Measurement uses no model calls.

Optimization defaults to **25 attempted model calls and 3600 elapsed seconds per
case per mode**, configurable with `--optimization-calls` and
`--optimization-seconds`. In full mode, Rust/source proposals, proof repair and
candidate repair share this single allowance. Model waits, compilation, proof
checks, tests and development measurements count toward the time limit. Failed
requests consume calls. Three validated candidates without a gain, an explicit
evidence-based finish, or either budget limit can end search. Retain the last
accepted incumbent; never promote an unvalidated pending candidate.
`--workers` controls independent case searches. Model waits may overlap;
compilation, Isabelle proofs, profiling and measurements share an exclusive
compute/timing lease. Waiting for this lease counts in the elapsed case budget.

Full mode may create a new Isabelle theory importing the original theories.
The controller supplies unconditional function-equality goals for **every**
original export, enforces checked proofs and rejects oracle dependencies. The
existing source extractor then rebuilds the SPG and dependency partition. The
translator sees that new graph before updating affected Rust, mappings and
guidance. These proofs relate source functions; they do not prove the Rust
translation. Frozen source tests and cached executed reference outputs must
also accept each new Rust candidate.

This stage retains existing Rust callable interfaces and the observation
connector. It permits new helpers and body changes, but rejects changes that
would require rebinding the frozen tests. Supporting representation changes
that alter these interfaces would require a separate explicit binding workflow;
the controller does not silently regenerate or weaken tests.

The search profiles a diagnostic instrumented copy, then selects on three
predeclared workloads (first, middle and primary, with duplicates removed).
Acceptance requires at least 3% geometric-mean improvement, the geometric mean
of the individual interval lower bounds above one, and no measured regression
over 5%. These are development decisions, not final statistical conclusions.
The final matrix measures **all** workloads independently with six process
rounds, rotating all six implementations, and reports regressions as well as
gains. Checked compilation occurs after selection under arbitrary semantics.

To extend a completed cohort without rerunning accepted cases, use a read-only
baseline collection. It records original run/release/checkpoint hashes and does
not claim those artifacts were freshly generated:

```sh
agent/.venv/bin/python -m i2r_agent.experiment_baselines \
  --run /absolute/first-eight --run /absolute/additional-two \
  --output /absolute/ten-case-baseline
```

Pass that collection directory as `--from-run` / `--baseline` above.

## Numeric interface

The versioned runtime is packaged in `agent/src/i2r_agent/numeric_runtime` and
vendored into each generated crate as a relative Cargo dependency. Its source
hash is part of the numeric contract and frozen configuration. It is not authored
or changed by the model. Both backends expose the same non-`Copy` types, owned and
borrowed operations, in-place addition/multiplication, conversions and errors.

- `arbitrary`: Dashu `UBig`/`IBig`, pinned to `dashu-int =0.6.2`.
- `checked`: `u128`/`i128`, explicit errors on unrepresentable intermediates and
  results; no wrapping, saturation or arbitrary-precision fallback.

Natural subtraction truncates at zero. Division by zero returns zero; modulo
zero returns the dividend. Signed division uses Isabelle's floor convention.
These runtime operations are available only where the actual source operation
has the same semantics. They do not authorize changing business algorithms.

## Comparison protocol

1. Retain the accepted arbitrary implementation, source-test evidence, exact
   source-to-Rust map, implementation guidance, observation connector, dependency
   configuration and executed reference output matrices.
2. Materialize arbitrary and checked builds from the **same business and
   connector file dictionaries**. Select a backend only through a Cargo feature.
   Require byte-identical business, connector, runtime and resolved lock files.
3. Compare both builds' complete ordinary and kernel outputs against the cached
   executed reference outputs. No reference executable is rerun and no source
   tests or connector are regenerated. Checked range failures are isolated and
   reported as exclusions, never counted as successful measurements. Original
   arbitrary large-value source tests and their execution evidence remain intact.
4. Rebuild timing-only drivers using the existing kernel-v2 implementation.
   Preparation, wire conversion and encoding are outside the measured section;
   intrinsic algorithm work, allocation, required copies and result storage are
   inside. The performance `acomp` wrapper proves its relation to the ordinary
   observer with an Isabelle lemma and moves AST construction/encoding outside
   the kernel. The original correctness wrapper is untouched.
5. Measure alternating backend order over five independent process rounds, with
   calibration, warmup and ten samples per process. Retain all raw records,
   instability notices, the predeclared primary workload, and every workload's
   `arbitrary_time / checked_time` ratio. The 95% interval resamples matched
   process rounds; it does not imply arbitrary-domain equivalence for checked.

Generic business functions stay generic. Numeric workload instantiations must
use the selected `Nat/Int`, including callback arithmetic; leaving raw `UBig`
elements in both builds would not measure the intended numeric ablation. The
controller rejects obvious measured-path wire work and raw wire result types.
This structural guard is incomplete, so actual connector timing boundaries and
generic instantiations still require inspection before interpreting results.

The matrix has three rows (off, Rust-only, Full) and two columns
(arbitrary, checked). Within each row business source is shared across columns.
Rust-only and Full must branch from the same off artifact with equal total
optimization budgets, and optimization choices are selected under arbitrary
before compiling the paired checked counterpart. Full may revise source theory,
but must carry source equivalence evidence and update affected guidance,
dependencies and mappings through the existing translation interfaces.
