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
| Code Optimization | Complete pipeline: [`cargo-opt.rs`](optimize/src/bin/cargo-opt.rs); analyses and cleanup passes: [`optimize/src/`](optimize/src/) |
