# Isabelle2Rust

Isabelle2Rust generates safe Rust from executable Isabelle/HOL specifications.
Stage-1 translates Thingol into baseline Rust, and Stage-2 applies
ownership-aware source-to-source optimizations.

## 1. Environment

The project was tested with:

- Ubuntu 22.04 under WSL2
- Isabelle/HOL 2025
- Rust 1.94.0
- OCaml 4.11.2
- Intel Core Ultra 9 185H and 15 GiB memory

## 2. Repository Structure

```text
Isabelle2Rust/
├── translate/              # Stage-1 Rust backend for Isabelle/HOL code generation
├── optimize/               # Stage-2 Rust ownership-aware code optimizer
├── test/
│   ├── HOL_Codegenerator/  # Official library-scale stress tests
│   ├── unit/               # Rule-level unit test suite
│   ├── fpp/                # Program-level test suite
│   ├── sbpf/               # Solana eBPF case study
│   └── x64/                # x86-64 semantics case study
├── evaluation/
│   ├── scripts/            # Generation, validation, and optimization scripts
│   └── results/            # Evaluation results
└── ROOT                    # Isabelle session definitions

RustLightAST/               # RustLight AST
```

`Isabelle2Rust/` and `RustLightAST/` must be sibling directories.

## 3. Installation

Install the system packages:

```bash
sudo apt update
sudo apt install -y \
  build-essential curl git make python3 perl util-linux \
  pkg-config libjansson-dev libgmp-dev opam m4 \
  cloc time libxi6 libxtst6 libxrender1 fontconfig
```

Install [Isabelle/HOL 2025](https://isabelle.in.tum.de/website-Isabelle2025/index.html)
and add its `bin` directory to `PATH`:

```bash
tar -xzf Isabelle2025_linux.tar.gz -C /YOUR/PATH
echo 'export PATH="/YOUR/PATH/Isabelle2025/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
isabelle version  # Isabelle2025
```

Install [Rust](https://rust-lang.org/tools/install/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup toolchain install 1.94.0 --profile minimal
rustup component add clippy rustfmt --toolchain 1.94.0
rustc +1.94.0 --version         # rustc 1.94.0
cargo +1.94.0 --version         # cargo 1.94.0
cargo +1.94.0 clippy --version  # clippy 0.1.94
rustfmt +1.94.0 --version       # rustfmt 1.8.0
```

Install OCaml for the SBPF and x86-64 experiments:

```bash
opam init -y
opam switch create isabelle2rust ocaml-base-compiler.4.11.2
eval "$(opam env --switch=isabelle2rust)"
opam install -y ocamlfind zarith yojson

ocamlopt -version             # 4.11.2
ocamlfind query zarith        # path ending in /zarith
ocamlfind query yojson        # path ending in /yojson
pkg-config --libs jansson     # contains -ljansson
```

Clone the two repositories into the required layout:

```bash
mkdir Isabelle2Rust-workspace
cd Isabelle2Rust-workspace

git clone https://github.com/OpenSourceVerif/RustLightAST.git
git -C RustLightAST checkout bec5b614d70afbb67041e12d800f7a8c2be502cc

git clone -b main https://github.com/OpenSourceVerif/Isabelle2Rust.git
cd Isabelle2Rust
```

## 4. Quick Start

Run the complete two-stage pipeline on one Isabelle theory:

```bash
make test DIR=test/example Name=RBT_Test
```

`RBT_Test` demonstrates code generation and optimization for a red-black tree.

Here, `DIR` contains the theory and `Name` is its filename without `.thy`. The command
generates and compiles the Stage-1 crate, applies Stage-2 optimization, and then
compiles the Stage-2 crate. The generated crates are written to:

```text
<DIR>/stage1/<Name>/export*/
<DIR>/stage2/<Name>/export*/
```
Omitting `Name` processes every `*_Test.thy` under `DIR`.

## 5. Stage-1: Code Translation

Stage-1 performs a syntax-directed translation from Thingol to baseline Rust.

```bash
make gen DIR=test/example Name=RBT_Test
```

### 5.1 Implementation

| Component | Implementation |
| --- | --- |
| Code Translation | Core translator: [`translate/code_rust.ML`](translate/code_rust.ML); code adaptations: [`translate/Rust_Base_Setup.thy`](translate/Rust_Base_Setup.thy), [`translate/Rust_BigInt_Setup.thy`](translate/Rust_BigInt_Setup.thy), and [`translate/Rust_Checked128_Setup.thy`](translate/Rust_Checked128_Setup.thy) |

## 6. Stage-2: Code Optimization

Stage-2 applies ownership-aware source-to-source optimizations to the generated baseline
Rust program.

```bash
make opt DIR=test/example Name=RBT_Test
```

This command applies the complete Stage-2 pipeline to an existing Stage-1
export.

### 6.1 Implementation

| Component | Implementation |
| --- | --- |
| Code Optimization | Complete pipeline: [`cargo-opt.rs`](optimize/src/bin/cargo-opt.rs#L320) |
| Supporting Ownership Refinements | Copyability analysis: [`copy_analysis.rs`](optimize/src/copy_analysis.rs#L118); local mutation recovery: [`mut_analysis.rs`](optimize/src/mut_analysis.rs#L22) |
| Last-use Clone Elimination | [`last_use_analysis.rs`](optimize/src/last_use_analysis.rs#L8) |
| Borrow Inference | [`borrow_analysis.rs`](optimize/src/borrow_analysis.rs#L407) |
| Structural Simplification | Pattern matches: [`match_cleanup.rs`](optimize/src/match_cleanup.rs#L179); closures: [`closure_cleanup.rs`](optimize/src/closure_cleanup.rs#L26); complex types: [`complex_type_cleanup.rs`](optimize/src/complex_type_cleanup.rs#L40) |

## 7. Testing and Benchmarks

The following commands run the test suites and benchmarks. Runs that may take several hours are noted below.

### 7.1 Code-Generation Capability

Code-generation tests cover the rule-level Unit tests, the program-level FPP suite, and Isabelle/HOL's official library-scale HOL-Codegenerator_Test (HCT).

```bash
make test DIR=test/unit
make test DIR=test/fpp
make hol-stress
```

The following scripts collect generated Rust lines of code (LOC) and translation and optimization times:

```bash
# Count generated Rust LOC
python3 evaluation/scripts/rq1/count-generated-loc.py

# Measure translation and optimization times
python3 evaluation/scripts/rq1/run-timings.py
```

#### Scripts and Results

| Component | Implementation and Results |
| --- | --- |
| Code-Generation Capability | HCT: [`test/HOL_Codegenerator/`](test/HOL_Codegenerator/); Unit: [`test/unit/`](test/unit/); FPP: [`test/fpp/`](test/fpp/); experiment scripts: [`evaluation/scripts/rq1/`](evaluation/scripts/rq1/); results: [`summary.csv`](evaluation/results/rq1/summary.csv) |

### 7.2 Behavioral Consistency

Behavioral consistency checks use differential testing at the program and instruction levels for SBPF and at the instruction level for x86-64.

#### SBPF-program

`make macro_sbpf` generates or reuses both Rust stages, then checks them and the OCaml export against native SBPF execution using 146 tests derived from Solana's official eBPF test suite.

```bash
# Run the 146 program-level tests
make macro_sbpf
# Success: each export reports Passed 146 / Failed 0 / Total 146,
# followed by Overall: PASS.
```

#### SBPF-instruction

`make micro_sbpf` generates or reuses both Rust stages, then checks them and the OCaml export against native SBPF execution using randomly generated instruction vectors. It uses 10,000 vectors by default; set `X` to change this number.

```bash
# Run 10,000 instruction-level tests
make micro_sbpf
# Run a custom number of tests
make micro_sbpf X=100000
# Success: each export reports Passed 10000 / Failed 0 / Total 10000
# for the default run, followed by Overall: PASS. With X set, the totals equal X.
```

#### x64-stepper

`make x64` generates or reuses both Rust stages, then checks them and the OCaml export against native x86-64 execution using randomly generated instruction vectors. It uses 10,000 vectors by default; set `X` to change this number.

```bash
# Run 10,000 instruction-level tests
make x64
# Run a custom number of tests
make x64 X=100000
# Success: each export reports Passed 10000 / Failed 0 / Total 10000
# for the default run, followed by Overall: PASS. With X set, the totals equal X.
```

Both SBPF and x86-64 reuse generated artifacts when the expected files are present and the relevant sources are unchanged. Set `REBUILD=1` to force regeneration.

The following scripts run the complete two-stage differential-testing campaigns over ten rounds of 100,000 vectors and may take many hours:

```bash
# Run the complete SBPF campaign
evaluation/scripts/rq2/run-sbpf-10x100k.sh
# Run the complete x86-64 campaign
evaluation/scripts/rq2/run-x64-10x100k.sh
```

#### Scripts and Results

| Component | Implementation and Results |
| --- | --- |
| Generated-code LOC | Script: [`count-generated-loc.py`](evaluation/scripts/rq2/count-generated-loc.py); results: [`generated-loc.csv`](evaluation/results/rq2/generated-loc.csv) |
| SBPF | Theory: [`test/sbpf/theory/`](test/sbpf/theory/); validation: [`run_macro_sbpf.py`](test/sbpf/tests/exec_semantics/run_macro_sbpf.py) and [`run_micro_sbpf.py`](test/sbpf/tests/exec_semantics/run_micro_sbpf.py); reproduction: [`run-sbpf-10x100k.sh`](evaluation/scripts/rq2/run-sbpf-10x100k.sh); results: [`evaluation/results/rq2/sbpf/`](evaluation/results/rq2/sbpf/) |
| x86-64 semantics | Theory: [`test/x64/theory/`](test/x64/theory/); validation: [`run_x64.py`](test/x64/x64-validation/run_x64.py); reproduction: [`run-x64-10x100k.sh`](evaluation/scripts/rq2/run-x64-10x100k.sh); results: [`evaluation/results/rq2/x64/`](evaluation/results/rq2/x64/) |

### 7.3 Optimization Effectiveness

Optimization benchmarks compare generated-code quality, runtime, and
heap allocation before and after Stage-2.

#### Code Quality

The following command compares Clippy diagnostics across the Stage-1 and
Stage-2 crates generated for the test suites in Section 7.1 and the SBPF and
x86-64 tests in Section 7.2.

```bash
make rq3-clippy
# Success: Recorded 93 crate pairs and 5900 -> 27 diagnostics in ...
```

The generated summary is written to
`evaluation/.work/rq3/code-quality/all/summary.csv`; the same directory also
records the run environment in `environment.json`.

#### Performance

The performance experiments compare Stage-1, full Stage-2, the Last-Use and
Borrow ablations, the Isabelle/HOL OCaml export, and the corresponding
case-study baseline.

```bash
# Measure SBPF-program on 146 tests and SBPF-instruction on 6,000 vectors
make rq3-sbpf
# Success: RESULT_DIR=.../evaluation/.work/rq3/sbpf/runs/<timestamp>

# Measure x64-stepper on 6,000 vectors
make rq3-x64
# Success: RESULT_DIR=.../evaluation/.work/rq3/x64/runs/<timestamp>
```

Each `RESULT_DIR` contains `environment.json`, an `experiment-record.md` with
the correctness results, and a `summary.csv` with three runtime and
heap-allocation measurements and their median. Recorded benchmark
results and environments are available under
[`evaluation/results/rq3/`](evaluation/results/rq3/); rerun performance values
may vary with the execution environment.

#### Scripts and Results

| Component | Implementation and Results |
| --- | --- |
| Code-quality improvement | Script: [`run-clippy.py`](evaluation/scripts/rq3/run-clippy.py); results: [`code-quality/`](evaluation/results/rq3/code-quality/) |
| Performance improvement | SBPF: [`run-sbpf.py`](evaluation/scripts/rq3/run-sbpf.py) and [`sbpf/`](evaluation/results/rq3/sbpf/); x86-64: [`run-x64.py`](evaluation/scripts/rq3/run-x64.py) and [`x64/`](evaluation/results/rq3/x64/) |
