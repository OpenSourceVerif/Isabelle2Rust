# AFP Isabelle2025 Rust export experiment

This directory discovers executable entry-owned constants from the **complete
AFP for Isabelle2025**, creates one explicit Rust export per entry, and records
loading, export, compilation, optimization and runtime validation separately.
It does not change the translator or optimizer.

## Dependencies

Follow the project README for Isabelle2025, Rust 1.94.0, and the sibling
../RustLightAST checkout used by the optimizer. Install the complete AFP archive:

~~~bash
curl -fLO https://isa-afp.org/release/afp-2025-03-17.tar.gz
# SHA256: c41fbd7b48d1023ddf6b34501eceb5480caf6e5bb6985905eeea0aef203ee4e3
tar -xzf afp-2025-03-17.tar.gz
mv afp-2025-03-17 /YOUR/PATH/afp-Isabelle2025
isabelle components -u /YOUR/PATH/afp-Isabelle2025/thys
isabelle version
~~~

To include theories whose ROOT condition requires Haskell, install Isabelle's
matching GHC after installing the project's system dependencies (including
libgmp-dev):

~~~bash
isabelle ghc_setup
~~~

Other optional compiler conditions are reported with any missing theories.

Remove/comment incompatible AFP registrations in the Isabelle2025 user ROOTS
or components file: registering multiple releases causes duplicate AFP chapters
and sessions. The scripts reject other Isabelle/AFP versions and incomplete AFP
subsets. The --afp option also accepts the archive's thys directory. Pass
--afp /YOUR/PATH/afp-Isabelle2025 to both scripts when AFP is installed elsewhere;
without this option they use Isabelle's AFP setting or temp/afp-Isabelle2025
inside this repository.

The 2025-03-17 release contains **893 entries, 922 sessions and 9,122 session-owned
theories**. sessions.scala uses Isabelle's session/dependency parser, including
subdirectories and multiple sessions per entry, rather than interpreting ROOT
files with regular expressions. The cached manifest is regenerable.

## Run

Execute commands from the repository root. Start with small entries, then scan
and run the full archive:

~~~bash
python3 test/afp-Isabelle2025/scan.py --entries Example-Submission List-Index
python3 test/afp-Isabelle2025/run.py --entries Example-Submission List-Index --stage2

python3 test/afp-Isabelle2025/scan.py
python3 test/afp-Isabelle2025/run.py --stage2
~~~

A full run.py invocation runs Example-Submission (empty scope) and List-Index
first, then every remaining entry. A failed entry does not stop independent
entries. Both scripts exit nonzero when any selected entry fails or remains
incomplete. Dependent entries whose AFP prerequisites failed to load are marked
blocked, rather than repeatedly rebuilding the same failed prerequisite.
Blocking follows the concrete session graph: a failed example/test session does
not block another entry which depends only on its successfully built core.

~~~bash
# Retry only incomplete scans, then incomplete exports/builds.
python3 test/afp-Isabelle2025/scan.py --retry-failed
python3 test/afp-Isabelle2025/run.py --retry-failed --stage2

# Restrict a run, or regenerate the theories/ROOT without compiling.
python3 test/afp-Isabelle2025/run.py --entries AVL-Trees
python3 test/afp-Isabelle2025/run.py --generate-only
~~~

The --stage2 option requests optimization and Stage-2 compilation; without it the
runner stops after compiling Stage 1. A prior Stage-1-only success is still selected
by --retry-failed --stage2. Editing the candidate scope invalidates an earlier
successful run. Runtime correctness is **not inferred** from Cargo compilation.
An independent semantic harness can be supplied explicitly:

~~~bash
python3 test/afp-Isabelle2025/run.py --entries List-Index --stage2 \
  --runtime-command 'python3 test/afp-Isabelle2025/check_runtime.py {entry} {stage1} {stage2}'
~~~

The included harness checks all 63 Boolean lists of lengths 0..5, comparing all
six exports to an independent Vec-based oracle (2,166 assertions per stage).
This is a finite semantic smoke test, not a proof of correctness.

The command is executed as an argument vector, without a shell. It must actually
check semantics; the generated crate's empty/default main is not a correctness
test. With no harness, runtime_validation.status stays not_run.

## Scope and results

- scan.ML inspects loaded constant declarations and their code certificates.
  Abbreviations and imported constants are excluded by declaration provenance.
  Equations declared in later entry theories are inspected in a merged context.
  When independent loaded branches have incompatible specifications or syntax,
  discovery falls back to their maximal theory contexts and unions candidates,
  preserving later equations along each branch. The merge conflict is recorded;
  an aggregate export may still fail to import those branches together.
  Ordinary, abstract and projection equations qualify. Certificate failures are
  retained as candidates and reported as diagnostics, so export failures cannot
  improve the apparent coverage by removing difficult constants.
- exports.json maps entry names to relative theory paths and fully qualified
  HOL constant names. It is the export scope; editing it is supported. The scanner
  never removes candidates merely because Rust export/compilation failed.
  Entries whose theories could not load remain visible, but their discovery is
  explicitly incomplete; an empty incomplete scan is not a successful empty entry.
  Missing theories list their ROOT compiler conditions separately. Install the
  corresponding external compiler and retry; enabled conditional sessions are
  rebuilt so a previously skipped theory cannot remain hidden in a cached heap.
- Each Entry/Entry_Rust_Export.thy imports the loaded AFP equation contexts and
  Rust.Rust_BigInt_Setup. It contains exactly one explicit export_code command
  for nonempty scopes, deduplicated by full name. Conditional compiler tests
  that never loaded are not added as unrelated imports; explicit candidates
  still request their defining theory. An empty scope emits no export
  command, especially no wildcard export.
- The marked block in the top-level ROOT declares an independent
  AFP-Rust-Entry session with AFP and Rust dependencies. Regeneration preserves
  the other sessions. Isabelle writes crates to
  Entry/stage1/Entry_Rust_Export/export*/; optimization writes the analogous
  stage2 directory.
- results.json is an atomic checkpoint after each entry. It records candidate/
  theory counts, scan completeness, separate phase statuses, command return codes,
  elapsed time, memory observations, error excerpts, and artifact/log paths.
  Global candidate and compiled-candidate coverage use distinct full HOL names.
  Old successful artifacts are removed before a new export, preventing a failed
  export from accidentally compiling an older crate.
- logs/ holds full command logs (ignored by Git); _build/ holds the regenerable
  session manifest, raw scan output, phase markers and the batch lock (also ignored).
  Reports retain short error excerpts for review even when local logs are absent.

AFP's generated Quickcheck narrowing instances are included when they have code
equations. Some depend on Haskell-only support without Rust code equations; these
are genuine recorded export failures, not silently filtered from this experiment.

## Resource bounds and cleanup

The scripts use one Isabelle job, one proof/ML thread, one Cargo job, a 3,000 MiB
ML heap limit, a 768 MiB Java heap limit, and a 600-second per-command timeout by
default. These settings are applied **after** initializing Isabelle's environment,
which would otherwise overwrite the heap limits. The batch used for the checked-in
results uses the resource limits recorded in results.json.

The options --timeout, --max-heap-mb, --java-heap-mb and --min-available-mb are
configurable. On Linux, a command is stopped if MemAvailable drops below 512 MiB.
Timeouts and interruptions stop descendant processes, including detached
bash_process groups. The Makefile's build lock prevents races with ordinary
project builds; a separate experiment lock serializes report writers.

Proofs are checked by default. The --skip-proofs option is an explicit exploratory
mode recorded in environment metadata; reports from checked and skipped proofs
cannot be mixed. A full scan/build can take many hours; inspect the atomic
checkpoint/logs or interrupt and use the retry options to continue.

Run the tooling regression tests and clean reproducible crates afterward:

~~~bash
python3 -m unittest discover -s test/afp-Isabelle2025 -p test_pipeline.py -v
python3 test/afp-Isabelle2025/check_scan.py
make clean
~~~

Generated export theories, exports.json, results.json, and logs survive make clean;
Stage-1/Stage-2 crates do not. Artifact paths in reports identify where the
corresponding successful build was performed, even after cleanup.

## Recorded rerun: 20261020T074609Z

The current checked-in JSON reports come from a fresh full rerun with proof
checking enabled and existing Isabelle heaps reused. See the [Chinese experiment
report](report/README.md) for the entry-to-export flow, exact configuration,
human-readable statistics, limitations and five retained case studies.

The rerun visited all 893 entries. Discovery completed for 438 entries and
retained 39,100 distinct full HOL constant names across 402 nonempty
entry scopes. Rust export succeeded for 41 entries; 26 compiled before and
after optimization. Compilation covers 153 distinct candidates. List-Index additionally
passed 2,166 independent assertions per stage (4,332 total).

The report includes a filterable [893-entry table](report/entries.csv),
[run provenance and commands](report/run.json), and [case evidence](report/cases/).
Original AFP theories, generated aggregate theories, raw diagnostics, Cargo
manifests/lockfiles and actual Rust sources are preserved for candidate-empty,
export-failed, compile-failed and successful examples. These copies use
rust-before/rust-after directories and survive make clean; target directories
and temporary phase work are removed. Raw batch console logs are retained as
text evidence inside the report; ordinary logs/ remains ignored.

## Exhaustive multilingual experiment

The separate `full/` output root preserves the earlier experiment in
`full/baseline/`. It is local experiment data, rather than a checked-in result.
Use the existing candidates, retry incomplete scans with checked proofs and no
time limit, then inspect each checkpoint before moving to the following stage:

~~~bash
python3 -B test/afp-Isabelle2025/scan.py --output-dir test/afp-Isabelle2025/full --retry-failed --timeout 0 --max-heap-mb 4500 --stack-space-mb 512 --compiler-settings test/afp-Isabelle2025/full/compiler-settings.json
python3 -B test/afp-Isabelle2025/full.py scan-checkpoint
python3 -B test/afp-Isabelle2025/full.py export
python3 -B test/afp-Isabelle2025/full.py export-checkpoint
python3 -B test/afp-Isabelle2025/full.py compile
python3 -B test/afp-Isabelle2025/full_audit.py --data-only
python3 -B test/afp-Isabelle2025/full_report.py
python3 -B test/afp-Isabelle2025/full_audit.py
~~~

Zero disables both the Python watchdog and Isabelle's command timeout. Memory
monitoring remains active. Compiler settings are an explicit JSON map of
`ISABELLE_*` environment variables; the full driver reads that file by default.
The official ML target is SML. Rust, SML, OCaml, Haskell, Scala and Go serialize
the same Thingol program in each valid context. Failed groups are split until
individual outcomes have direct evidence. Independent incompatible theory
branches remain separate, and their aggregate merge error is also preserved.

Every attempt retains its full exception XML, process log and successful
sources. Failed session databases are copied before printing unfiltered messages;
their timestamps and return codes must match the referenced failed builds.
Auxiliary prerequisite builds recorded under `full/prerequisites/` must finish
successfully before exports begin. A checkpoint refuses unresolved resource,
environment or tool failures.

Compilation uses actual successful Rust manifests, attempts Stage-1, optimization
and Stage-2 independently, and never executes generated programs. Exported
sources in `full/exports/` and optimized sources in `full/rust-stage2/` survive
the ordinary cleanup rules for directories named `stage1` or `stage2`.
Preserve those source trees and all evidence when clearing reproducible caches.

The report contains four Markdown documents, entry/candidate/crate CSV catalogs
and full failure bodies in JSONL. Final generation requires a current independent
data audit. The completion audit checks physical XML witnesses, source hashes,
actual Cargo commands, distinct compiled coverage, every report row and every
failure occurrence. Representative mechanism explanations still require review
against the original HOL definitions and code-generator implementation.
`--preview` on either reporting script explicitly marks incomplete output and
cannot certify completion.

Run the complete lightweight tooling regression suite with:

~~~bash
python3 -B -m unittest discover -s test/afp-Isabelle2025 -p 'test_*.py' -q
~~~

Long commands also write an atomic JSON sidecar beside their text log before
waiting for completion. It includes the command, PID, Linux birth identity and
boot ID; terminal outcomes preserve interruption and resource failures. A
sidecar marked running is evidence of intent only: verify its process identity
before resuming. Archived host-interruption observations belong to historical
infrastructure events and do not condemn any HOL candidate.

Use --java-active-processors to bound JVM worker and native-thread memory
(default: 2), independently of the existing one-thread ML proof setting.
