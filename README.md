# Isabelle2Rust

Isabelle2Rust generates safe Rust from executable Isabelle/HOL specifications.
It uses a two-stage pipeline: Stage 1 translates Thingol programs into
compiler-accepted Rust, and Stage 2 applies ownership-aware optimizations.

## 1. Environment

The artifact was evaluated with:

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
│   ├── scripts/            # RQ1–RQ3 experiment scripts
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
isabelle version
```

Install  [Rust](https://rust-lang.org/tools/install/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup toolchain install stable --profile minimal
rustup component add clippy --toolchain stable
rustc +stable --version
cargo +stable --version
```

Install OCaml for the SBPF and x86-64 experiments:

```bash
opam init -y
opam switch create isabelle2rust ocaml-base-compiler.4.11.2
eval "$(opam env --switch=isabelle2rust)"
opam install -y ocamlfind zarith yojson

ocamlopt -version
ocamlfind query zarith
ocamlfind query yojson
pkg-config --libs jansson
```

Clone the two repositories into the required layout:

```bash
mkdir Isabelle2Rust-artifact
cd Isabelle2Rust-artifact
git clone https://github.com/OpenSourceVerif/RustLightAST.git
git clone https://github.com/OpenSourceVerif/Isabelle2Rust.git
cd Isabelle2Rust
```

## 4. Quick Start

Run the complete two-stage pipeline on one Isabelle theory:

```bash
make test DIR=test/unit/mapping Name=Lists_Test
```

`DIR` contains the theory and `Name` is its filename without `.thy`. The command
generates and compiles the Stage-1 crate, applies Stage-2 optimization, and then
compiles the Stage-2 crate. The generated crates are written to:

```text
<DIR>/stage1/<Name>/export*/
<DIR>/stage2/<Name>/export*/
```

Omitting `Name` processes every `*_Test.thy` under `DIR`.

## 5. Stage 1: Code Translation

Stage 1 translates Thingol programs into safe Rust Cargo crates using a
conservative owned-and-clone discipline.

```bash
make gen DIR=test/unit/mapping Name=Lists_Test
```

### 5.1 Link to Paper

| Paper | Code |
| --- | --- |
| Code Translation (Section 4) | Core translator: [`translate/code_rust.ML`](translate/code_rust.ML); code adaptations: [`translate/Rust_Base_Setup.thy`](translate/Rust_Base_Setup.thy), [`translate/Rust_BigInt_Setup.thy`](translate/Rust_BigInt_Setup.thy), and [`translate/Rust_Checked128_Setup.thy`](translate/Rust_Checked128_Setup.thy) |

## 6. Stage 2: Code Optimization

Stage 2 analyzes the generated Rust program and applies source-to-source
transformations that refine ownership and simplify program structure.

```bash
make opt DIR=test/unit/mapping Name=Lists_Test
```

This command applies the complete Stage-2 pipeline to an existing Stage-1
export.

### 6.1 Link to Paper

| Paper | Code |
| --- | --- |
| Code Optimization (Section 5) | Complete pipeline: [`cargo-opt.rs`](optimize/src/bin/cargo-opt.rs#L320) |
| Supporting Ownership Refinements (Section 5.1) | Copyability analysis: [`copy_analysis.rs`](optimize/src/copy_analysis.rs#L118); local mutation recovery: [`mut_analysis.rs`](optimize/src/mut_analysis.rs#L22) |
| Last-use Clone Elimination (Section 5.2) | [`last_use_analysis.rs`](optimize/src/last_use_analysis.rs#L8) |
| Borrow Inference (Section 5.3) | [`borrow_analysis.rs`](optimize/src/borrow_analysis.rs#L407) |
| Structural Simplification (Section 5.4) | Pattern matches: [`match_cleanup.rs`](optimize/src/match_cleanup.rs#L179); closures: [`closure_cleanup.rs`](optimize/src/closure_cleanup.rs#L26); complex types: [`complex_type_cleanup.rs`](optimize/src/complex_type_cleanup.rs#L40) |

## 7. Evaluation

### 7.1 RQ1: Code-Generation Capability

RQ1 uses three complementary test suites:

- **HCT** is Isabelle/HOL's official library-scale code-generation stress test.
- **Unit** exercises the translation and optimization rule families.
- **FPP** evaluates their composition in program-level developments.

```bash
make hol-stress
make test DIR=test/unit
make test DIR=test/fpp
```

#### Link to Paper

| Paper | Code |
| --- | --- |
| RQ1: Code-Generation Capability (Section 6) | HCT: [`test/HOL_Codegenerator/`](test/HOL_Codegenerator/); Unit: [`test/unit/`](test/unit/); FPP: [`test/fpp/`](test/fpp/); experiment scripts: [`evaluation/scripts/rq1/`](evaluation/scripts/rq1/) |

### 7.2 RQ2: Behavioral Consistency

The SBPF experiments compare the generated Rust with the corresponding OCaml
export and the Solana reference implementation.

```bash
make micro_sbpf_gen X=100000
make macro_sbpf
make micro_sbpf
```

The x86-64 experiments compare the generated stepper with the OCaml export and
native x86-64 execution.

```bash
make x64-gen
make x64-test
make x64
```

The paper-scale experiments run ten rounds of 100,000 test vectors:

```bash
evaluation/scripts/rq2/run-sbpf-10x100k.sh
evaluation/scripts/rq2/run-x64-10x100k.sh
```

#### Link to Paper

| Paper | Code |
| --- | --- |
| SBPF (RQ2, Section 6) | Export declarations: [`bpf_generator_bigint.thy`](test/sbpf/theory/bpf_generator_bigint.thy#L13) and [`bpf_generator_checked128.thy`](test/sbpf/theory/bpf_generator_checked128.thy#L15); program-level runner: [`run_macro_sbpf.py`](test/sbpf/tests/exec_semantics/run_macro_sbpf.py#L225); instruction-level runner: [`run_micro_sbpf.py`](test/sbpf/tests/exec_semantics/run_micro_sbpf.py#L225) |
| x86-64 semantics (RQ2, Section 6) | Formal model: [`test/x64/theory/`](test/x64/theory/); Rust export: [`run_rust_export.py`](test/x64/x64-validation/run_rust_export.py#L287); differential testing: [`run_rust_validation.py`](test/x64/x64-validation/run_rust_validation.py#L217) |

### 7.3 RQ3: Optimization Effectiveness

RQ3 evaluates generated-code quality and the performance of `SBPF-program`,
`SBPF-instruction`, and `x64-stepper`.

```bash
make rq3-clippy
make rq3-sbpf
make rq3-x64
```

#### Link to Paper

| Paper | Code |
| --- | --- |
| Code-quality improvement (RQ3, Section 6) | [`evaluation/scripts/rq3/run-clippy.py`](evaluation/scripts/rq3/run-clippy.py#L264) |
| Performance improvement (RQ3, Section 6) | SBPF: [`evaluation/scripts/rq3/run-sbpf.py`](evaluation/scripts/rq3/run-sbpf.py#L1251); X64: [`evaluation/scripts/rq3/run-x64.py`](evaluation/scripts/rq3/run-x64.py#L1225) |
