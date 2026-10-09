# Isabelle2Rust

Isabelle2Rust generates safe Rust from executable Isabelle/HOL specifications.
Stage-1 translates Thingol into baseline Rust, and Stage-2 applies
ownership-aware source-to-source optimizations.

## 1. Environment

The project was tested with:

**Hardware and operating systems**

- Linux: Ubuntu 22.04 under WSL2, Intel Core Ultra 9 185H, 15 GiB memory
- macOS: macOS 26.5.1, Apple M5 (arm64), 16 GiB memory

**Software dependencies**

- Isabelle/HOL 2025
- Rust 1.94.0
- Python 3 (3.9.6 on the macOS test machine)
- OCaml: 4.11.2 on Linux; 4.14.2 on macOS (Apple Silicon)

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

#### Install the system packages:

**Linux (Ubuntu / WSL2)**

```bash
sudo apt update
sudo apt install -y \
  build-essential curl git make python3 perl util-linux \
  pkg-config libjansson-dev libgmp-dev opam m4 \
  cloc time libxi6 libxtst6 libxrender1 fontconfig
```

**macOS**

#### Install the Xcode Command Line Tools and the packages through [Homebrew](https://brew.sh/):

```bash
xcode-select --install
brew install python git make perl pkg-config jansson gmp opam m4 cloc gnu-time
```

#### Install [Isabelle/HOL 2025](https://isabelle.in.tum.de/website-Isabelle2025/index.html) and add its `bin` directory to `PATH`:

**Linux**

```bash
tar -xzf Isabelle2025_linux.tar.gz -C /YOUR/PATH
echo 'export PATH="/YOUR/PATH/Isabelle2025/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
isabelle version  # Isabelle2025
```

**macOS**

```bash
tar -xzf Isabelle2025_macos.tar.gz -C /Applications
echo 'export PATH="/Applications/Isabelle2025.app/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
isabelle version  # Isabelle2025
```

#### Install the [AFP release for Isabelle2025](https://isa-afp.org/download/) for the `Word_Lib` session, then register its theories directory on either platform:

```bash
isabelle components -u /YOUR/PATH/afp/thys
```

#### Install [Rust](https://rust-lang.org/tools/install/):

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

#### Install OCaml for the SBPF and x86-64 experiments:

**Linux**

```bash
opam init -y --bare
opam switch create isabelle2rust ocaml-base-compiler.4.11.2
```

**macOS**

```bash
opam init -y --bare
opam switch create isabelle2rust ocaml-base-compiler.4.14.2
```

On both platforms, activate the switch and install the libraries:

```bash
eval "$(opam env --switch=isabelle2rust)"
opam install -y ocamlfind zarith yojson

ocamlopt -version             # Linux: 4.11.2; macOS: 4.14.2
ocamlfind query zarith        # path ending in /zarith
ocamlfind query yojson        # path ending in /yojson
pkg-config --libs jansson     # contains -ljansson
export OCAML_VERSION="$(ocamlopt -version)"
```

`OCAML_VERSION` selects the version expected by the SBPF test runners.

Clone the two repositories into the required layout:

```bash
mkdir Isabelle2Rust-workspace
cd Isabelle2Rust-workspace

git clone -b main https://github.com/OpenSourceVerif/RustLightAST.git

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
