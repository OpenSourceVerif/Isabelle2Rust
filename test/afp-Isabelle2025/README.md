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

## Recorded batch: 2026-10-20

The checked-in reports cover the complete 2025-03-17 release: **893 entries,
922 original sessions and 9,122 owned theories**. Discovery inspected 3,449 of
those theories and retained **38,936 distinct full HOL constant names** across
400 nonempty entry scopes. All 893 aggregate theories and independent ROOT
sessions were generated, including explicit empty/incomplete entry records.
Proof checking remained enabled throughout.

| Phase | Passed entries | Other outcomes |
| --- | ---: | --- |
| Discovery | 436 | 19 failed; 438 blocked |
| Rust export | 41 | 348 failed; 2 timed out; 464 blocked; 38 empty scopes |
| Stage-1 compilation | 26 | 15 failed; 852 not run |
| Optimization | 26 | 867 not run |
| Stage-2 compilation | 26 | 867 not run |
| Independent runtime harness | 1 | 892 not run |

The final entry statuses are 25 passed, 1 partial, 38 no_candidates, 373 failed
and 456 blocked. The partial entry is Go: both Rust stages compiled its two
collected candidates, but four conditional theories require ISABELLE_GOEXE.
Each successful compilation stage covers **153 distinct candidates**. The
List-Index runtime check covers six of those candidates with 2,166 independent
assertions per stage, **4,332 total**. Compilation and this finite runtime test
are separate evidence; neither establishes correctness of all AFP exports.

The initial full scan used a 180-second per-command bound, and the 718-entry
retry used 600 seconds. Export, Cargo and optimization commands used 180 seconds.
HOL-Library was prepared separately with an 1,800-second bound and 4,500 MiB ML
heap, completing in 403.78 seconds; ordinary commands retained the 3,000 MiB ML
limit. Java used 768 MiB; Isabelle and Cargo remained serial. The 512 MiB
available-memory guard stopped Posix-Lexing rather than allowing an OOM crash.
HOL-Analysis exceeded its 600-second preparation bound, blocking 434 subsequent
entries. These failures were retained rather than reported as empty successes.

The remaining failures include missing dependency equations (notably generated
Quickcheck narrowing support), incompatible theory branches, code-generator
errors and Rust type/trait errors. No candidates were filtered to improve the
reported success rate. The four entries affected by incompatible synthetic
merges were re-scanned after adding branch-context discovery; their aggregate
export outcomes remain independent of discovery success.

Validation also passed 21 tooling regression tests and two actual Isabelle
scanner cases. The scanner cases check declaration provenance, later-added
code equations, abbreviations, absent equations and conflicting class instances
in independent branches. The tooling tests check scope invalidation, failure
isolation, retained import diagnostics, conditional theories, safe cleanup and
termination of detached child processes. The final audit verified all scopes,
phase states, coverage, artifact manifests and preservation of the original ROOT.

results.json includes the dated batch snapshot, prerequisite preparation,
execution return codes, resource bounds, compiler conditions and validation
records. Generated crates and raw _build data are cleaned after verification;
theories, reports and local logs remain. Logs are not committed. Re-run the
scripts to regenerate crates before inspecting or executing their artifacts.
