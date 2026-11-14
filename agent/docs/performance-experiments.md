# Optional performance experiments

The default correctness pipeline is unchanged. The performance stage consumes a
validated artifact only after the original source tests and differential tests
have passed.

## Configuration

- `--arbitrary` and `--checked` retain the existing generation profiles.
- `--paired-numerics` opts into one generated business implementation using
  `i2r_numeric::Nat` / `Int`. Its two builds differ only in the runtime feature:
  Dashu `UBig` / `IBig`, or checked `u128` / `i128`.
- `--off` is the default optimization mode. `--rust-only` searches Rust
  implementations with a fixed source model. `--full` additionally permits
  proof-checked Isabelle source transformations.
- `--optimization-calls` and `--optimization-seconds` default to 25 and 3600
  **per case per optimization mode**. Full shares this allowance across source
  proposals, proof repair, Rust changes, compilation, validation and measurement.
  Failed or interrupted model requests remain charged. Compute queue time is
  included. Exhaustion retains the last validated and faster incumbent.
  Scope reviews occur before accepting a candidate and consume the same budget.
  Finalization selects only preapproved, behaviorally validated candidates; it
  does not add a new model search or retrospectively relax eligibility.
- Full's phase allocation is configurable with `--source-calls`,
  `--source-seconds`, `--rust-reserve-calls`, and `--rust-reserve-seconds`.
  These options require `--full`, are frozen with the experiment, and must fit
  the total call/time limits. The existing allocation remains the default.
  These are caps and reserves, not a requirement to spend the budget.

`--paired-numerics` intentionally creates a new numerical experiment. Existing
correctness artifacts and their results remain intact. It does not claim that
new paired artifacts are byte-identical to an earlier Dashu-only generation.
With no performance flags, the previous prompts, configuration and generation
contract are preserved. The default `--off` path also retains the ordinary
`Executor` launch and cleanup behavior; owned-process tracking is enabled only
for the performance `BudgetExecutor`. Exact replay evidence is archived with
this study.

## Workflow

1. Freeze the passed checkpoint, generated code, source model, global guidance,
   source-to-Rust mapping, source tests, connector, inputs and executed reference
   outputs. An optional baseline collection references immutable existing runs.
2. In paired mode, compile the same business files and connector with each numeric
   backend. Check cached expected outputs without rerunning reference programs.
3. Profile the arbitrary backend with the full source graph, guidance and mapping.
   Rust-only proceeds directly to fixed-source Rust refinement. Full first
   considers a bounded source phase: at most two transformation directions.
   Source proposal uses its own stage prompt: source and Rust gains are
   complementary, so a smaller source gain is not rejected merely because
   ownership fixes promise more. A concrete work reduction with a plausible
   proof route gets bounded investigation, including reasonable local repairs.
   Source proposals may change algorithms; existing lowering choices are
   baseline context. The ordinary Rust policy resumes after proof/extraction.
   No source success quota weakens proof, validation, or timing acceptance.
   The default allocation is ten model calls/twenty minutes, reserving twelve
   calls/thirty minutes for Rust within the total 25-call/one-hour cap; explicit
   experiment configuration can change that allocation without changing Off.
   The reported source allowance already subtracts this Rust reserve; it must
   not be subtracted a second time. Source proposals may change an algorithm or
   recurrence when the required equality is proved. The fixed-recurrence rule
   applies to the subsequent Rust phase, not to source proposals. Private source
   helpers are allowed; each original export still needs its wrapper and proof.
   The replacement protocol supplies each original export's actual source type;
   generic internal helpers do not make a concrete entry polymorphic. General
   mathematical case distinctions may be source-proved for the full original
   domain and then realized in Rust; benchmark matching and answer tables remain
   forbidden. The same distinction applies to source planning, realization and
   admission. Unknown direction labels beyond the two registered slots receive
   recoverable feedback before proving; a repair can reuse its registered ID,
   while a genuinely new direction cannot bypass the quota. Every such model
   response still consumes the unchanged call/time budget.
   A source opportunity must identify the measured cost, concrete transformation
   and same-type unconditional equality obligation. Prove every exported root,
   re-extract the graph and dependency partition, and realize the revised graph
   in Rust with updated mapping/guidance. Proofs, repairs, translation and its
   initial performance screen all consume this source allowance. Mere theorem
   citations do not bypass proof and extraction. Accept at most one source
   transformation; if none survives validation and timing, restore the complete
   original state. This conservative screen may miss changes needing extensive
   later Rust tuning. The original artifact and source files remain immutable.
   Before the first source feasibility decision, Full automatically receives
   frozen defining-theory context for its exported roots and direct callees
   (at most three theories and 24,000 characters). Short theories are included
   completely; long theories use explicit windows around the definitions. The
   context and coverage limits are recorded. This prevents a proof-cost guess
   based solely on the execution graph from silently replacing theory inspection.
   Both modes may use `inspect` with the existing `request_sources` range format
   to read frozen theory text and actual named lemmas. Reads consume model calls
   and elapsed budget, but are not candidate failures or new source directions.
   Source proposals containing decoded mathematical Unicode are encoded using
   the configured Isabelle symbol tables before lexing/proving. The original
   proposal, effective text and symbol-table hashes are retained; this does not
   change proof goals or repair proof logic.
4. Compile the proposal; execute the frozen source tests and compare the existing
   connector outputs against cached reference observations. No test or connector
   regeneration, original reference execution, or original translation rerun.
Review JSON may mechanically move top-level evidence into a single review only
when there is exactly one review and no duplicate fields. Values are unchanged,
the original reply is retained, and the full semantic validator still runs.
Ambiguous evidence is rejected. A malformed or truncated reply gets at most one
charged format repair; a valid semantic rejection is not retried.

5. Review each candidate against its current source equations before timing or
   accepting it. The review excludes measured runtimes and the proposal's
   rationale; comments and mapping descriptions remain visible as author claims,
   not proofs. Review evidence is cached against its complete supplied context.
   Source equations and verified runtime contracts take precedence over
   conflicting analysis prose. A baseline-to-candidate difference establishes
   which code changed; it does not prove inherited code correct or waive a real
   abstraction invariant. Candidate admission concerns the current business
   computation and obligations introduced or activated by the candidate. Record
   inherited baseline findings separately under the same baseline identity for
   every mode. A reported violation affecting a declared export, including a
   violation whose root relevance remains unknown, holds the entire case before
   build or timing, including Off, Rust-only and Full. An unknown inherited
   concern or missing all-input proof stays in the report; it does not replace
   the original correctness workflow's qualification with a stronger admission
   requirement. New or activated candidate obligations still require the strict
   candidate review. An unrelated stronger helper/API claim is
   recorded as a claim limitation, not silently upgraded to a source contract.
   Frozen correctness validation remains executed evidence, not a mathematical
   proof of the baseline.
   Operation-order evidence uses shared event identifiers
   so that different wording cannot itself be mistaken for changed computation.
   Pure list-spine storage writes are distinguished from element computations
   and domain constructors. Forward push versus iterator map/extend alone does
   not change a map's logical visits or callback order. Reordering callbacks,
   recursive children or emitted domain instructions still needs a source proof.
   A malformed review may receive one charged schema repair on the identical
   candidate/context. Valid semantic decisions are never retried until approval.
   Local swapping of a commutative primitive's operands requires a law tied to
   the current typed execution equation and a verified runtime contract with
   identical value and overflow/error domains. It may not change evaluation
   order, operation count, association, recursion, or visitation. In particular,
   this does not permit reassociation of checked arithmetic.
   For a generic implementation, inspect default helper bodies and concrete
   overrides as well as the source class laws. Correct Nat/Int implementations
   do not establish arbitrary external trait implementations. Newly overridable
   arithmetic helpers can add a coherence obligation even when their default
   bodies are correct; both optimization modes must preserve the same original
   generic contract. A syntax check freezes existing visible trait member sets
   before compilation and rechecks older selected artifacts before new matrix
   measurements. Default bodies and `doc(hidden)` do not exempt new override
   points; existing method-body optimization and private free helpers remain
   allowed.
   Private free helpers are implementation details: their signatures may change,
   or the helpers may be renamed/removed together with callers and mappings.
   Public/restricted-public functions, exported linker symbols, trait members
   and impl members retain interface checks. Frozen source tests and connectors
   are still compiled and executed after an internal refactor.
6. Compare the candidate and incumbent on predeclared development workloads.
   Accept only measured gains under the recorded rule. Keep every rejected
   proposal, diagnostic, measurement and budget reservation. With the chosen
   source fixed, run Rust refinement rounds until three consecutive validated
   candidates are unaccepted, no concrete worthwhile action remains, or the
   budget ends. Invalid JSON, incomplete review schemas and failed compilation
   still consume the total budget, but do not masquerade as validated no-gain
   candidates for this early stop.
   Do not return to source search. A rejected candidate cannot become the context
   or incumbent for later optimization. Preserve original polymorphic types.
   Source skip, failure, or phase-budget exhaustion restores the accepted
   incumbent and enters this same Rust phase. Full's Rust proposals use the same
   admission rules as Rust-only; source success is not a prerequisite.
   Full and Rust-only are independent bounded searches from the same A0; Full
   need not beat Rust-only and does not secretly run a second Rust-only branch.
7. Freeze the selected Off, Rust-only and Full states. Independently measure all
   six cells using fresh process rounds and unchanged declared workloads. Byte-
   identical business/connector code and numeric configuration share one build
   and measurement, explicitly recorded as aliases. Other executables receive
   at least six process rounds in complete Williams-balanced order cycles, ten samples per process, with
   a predetermined forty samples for batches short relative to the timer probe.
   There is no repeat-until-faster rule or overhead subtraction. Short-batch
   warnings and empirical empty-batch/timer-probe fractions remain in raw data;
   their point estimates must not be presented as exact nanosecond effects.
   Final measurements never feed back into search.

Source transformation proves HOL equivalence, not Rust equivalence. Isabelle runs
with proofs enabled; a positive outer-command allowlist and oracle-dependency
audits cover the equality theorems and reachable executable equations. Rust still
requires the existing behavioral checks.

Checked overflow is an explicit range exclusion, never wrapping or arbitrary
precision fallback. Report exclusions and compare numeric backends only on
common valid workloads. Keep types, generic bounds and observable interfaces
fixed; local parameter names and `mut` bindings may change.

## Commands

`--dataset performance` and `--dataset performance-source` select their respective
fixed manifests. Inspect the selected manifest for roots, inputs and source hashes.
These are targeted cohorts, not unbiased samples of the broader corpus.

The optional performance module recomputes an exact primitive-adapter catalog
from the current extracted graph. This includes newly introduced library
arithmetic after a source proof. The author must explicitly declare a proposed
boundary and update affected mappings/guidance; availability never silently
changes the partition. Source identity, type, non-business status and the frozen
paired-runtime hashes must all match. The same catalog and active contracts are
provided to Rust-only, Full and admission. The original correctness defaults and
Off path are unchanged. A custom repeated-addition multiplication cannot be
replaced by a native multiplication under this rule; Full first needs a checked
source equivalence that introduces the registered library multiplication.
Contracts are trusted backend lowering rules, not a proof of generated Rust.

Source qualification distinguishes no applicable work reduction, proof-search
failure within the budget, translation/admission failure, and lack of measured
gain. Incomplete model output is a charged protocol/resource failure, not
evidence that source optimization is mathematically impossible. In particular,
do not classify a missing library adapter as an inherent source limitation, or
count a proved change that is translated back into the original expensive work
as a successful source improvement.

Use the repository's normal tool/credential configuration. For a fresh paired
baseline:

```sh
python -m i2r_agent.fpp_runner --dataset performance --run RUN --paired-numerics --off pipeline
python -m i2r_agent.fpp_runner --dataset performance --run RUN measure
```

After the baseline is frozen, optimize independent modes:

```sh
python -m i2r_agent.fpp_runner --dataset performance --run RUST_RUN --paired-numerics --rust-only --workers 3 optimize --from-run BASELINE
python -m i2r_agent.fpp_runner --dataset performance --run FULL_RUN --paired-numerics --full --workers 3 optimize --from-run BASELINE
python -m i2r_agent.optimization_matrix --baseline BASELINE --rust RUST_RUN --full FULL_RUN --output MATRIX
```

To use completed cases from multiple original runs, create an explicit reference
collection for each optimization mode:

```sh
python -m i2r_agent.optimization_experiments --mode rust-only \
  --case CASE_A=RUST_RUN_A --case CASE_B=RUST_RUN_B --output RUST_SOURCES \
  --reason "Documented case-to-run assignment" --plan EXPERIMENT_PLAN
python -m i2r_agent.optimization_matrix --baseline BASELINE --rust RUST_SOURCES --full FULL_SOURCES --output MATRIX
```

Create `FULL_SOURCES` in the same way with `--mode full`. Collections seal
references to the original reports, selected states, scope decisions and output
hashes; they do not copy code, invent a replacement run, or reuse timing samples.
When referenced runs have different release identities, `--reason` and `--plan`
are required and the plan file is hash-sealed. Register the case-to-run assignment
before final measurement and report the mixed releases explicitly. Choose runs
by that plan, not by which candidate is faster; final measurement remains fresh.

Runs reject changed implementation, inputs, dependencies or configuration. The
source-first controller uses stage schema 2; an unfinished older-schema search
cannot silently resume with the new ordering. Old outputs stay readable and
separate from new experiments. Preparation uses shared timing locks and at most
two preparation slots across controller processes. Measurements use an exclusive
lock; waiting is recorded and still counts toward the elapsed budget.

The performance `BudgetExecutor` tracks command-owned descendants, including
processes that detach into another session. On completion, timeout or interruption,
it verifies process identities and performs bounded cleanup within the command's
time allowance. Cleanup records are separate from command results. If cleanup
cannot be verified, the optimization aborts instead of treating it as an ordinary
rejected candidate. A persistent `agent/cache/timing-v2.cleanup-hold.json` blocks
further performance preparation and timing, including final matrix measurements.
Release this hold only after verifying that the recorded command-owned processes
are gone and resolving any unverified identities; retain the evidence for that
explicit release. Normal correctness execution neither reads nor writes this hold.
Optional diagnostic profiling may be unavailable without stopping optimization,
but it must propagate command-ownership or cleanup failures. Such failures cannot
be converted into an ordinary missing-profile result and followed by more search.
