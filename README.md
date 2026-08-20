# Isabelle2Rust Artifact (AE Branch)

This repository contains the **artifact evaluation (AE) version** of the Isabelle2Rust toolchain submitted to FM2026.

Active development of Isabelle2Rust continues on the **dev branch**.

The most recent updates can be found at:

👉 https://github.com/shenghaoyuan/Isabelle2Rust/tree/dev

## 1. Introduction

The repository consists of these major components:

- **`code_rust.ML`** : the core of the Isabelle2Rust backend, implemented in Poly/ML. Link to paper‘s Section3.
- **`Rust_Target.thy`**: Rust target registration and serialization support
  without code adaptations.
- **`Rust_Base_Setup.thy`**: representation-independent Rust mappings.
- **Numeric profiles**: import exactly one complete profile for `integer`,
  `int`, and `nat`:
  - `Rust_BigInt_Setup.thy`: all three numeric types use arbitrary precision.
  - `Rust_Checked128_Setup.thy`: raw `i128`/`u128` values with checked
    overflow.
- **Word profiles**: when Isabelle words are required, select the matching
  `Rust_BigInt_WordU128_Setup.thy` or
  `Rust_Checked128_WordU128_Setup.thy` entry point.
- **Internal layer**: `Rust_Integer_BigInt_Layer.thy` is reserved for tests
  that intentionally keep Isabelle's binary-natural representation.
- **`tests_HOL/`** : a collection of 7 official `HOL codegenerator_tests`, evaluates to a Boolean result. Link to paper's Section 4.
- **`tests_targeted/`** : a suite of 41 targeted test cases designed to exercise representative translation scenarios. All tests compile and execute successfully via Cargo. Link to paper's Section 4.
- **`test/eval/`**: the frozen, paper-facing RQ3 performance data included in
  the review artifact. Exploratory measurement logs are intentionally excluded.

## 2. Hardware Dependencies

Note that we only test our project on:

- Windows 11 + WSL2 (Ubuntu 22.04 LTS)
- Ubuntu 22.04 LTS

plus `CPU: Intel(R) Core(TM) Ultra 7 155H   2.50 GHz` + `RAM 32G` + `Core: 16`

## 3. Getting Started Guide

 This guide will help you set up the necessary environment within approximately 10 minutes.

### 3.1 Set up

- **Rust**
  - Installation Instructions:  [Rust Installation](https://rust-lang.org/tools/install/)
  - For our environment:

```bash
rustup --version
#rustup 1.28.2 (e4f3ad6f8 2025-04-28)

# install the stable toolchain used by the artifact
rustup toolchain install stable
# go to our repo folder
cd /OUR-REPO
# rust-toolchain.toml selects stable in this repository
# check version
cargo --version && rustc --version
# expected: cargo 1.94.0 (85eff7c80 2026-01-15)
# expected: rustc 1.94.0 (4a4ef493e 2026-03-02)
```

- **[Isabelle/HOL 2025](https://isabelle.in.tum.de/)**
  - Installation Path: `/YOUR-PATH/Isabelle2025`

```bash
# set isabelle PATH and update shell environment
vim  ~/.bashrc # export PATH=$PATH:/YOUR-PATH/Isabelle2025/bin:...
source ~/.bashrc

# check version
isabelle version 
# expected：Isabelle2025
```

- Other dependencies

```bash
sudo apt install make
```

- Fixed environment for sBPF macro validation

The sBPF macro validation target runs both the OCaml and Rust versions exported
from `tests_sbpf/theory/bpf_generator.thy`. The OCaml side is fixed to
`ocamlc 4.11.2` with `ocamlfind` and `zarith`:

```bash
# one possible setup path
opam switch create 4.11.2 ocaml-base-compiler.4.11.2
eval $(opam env --switch=4.11.2)
opam install zarith

ocamlc -version
# expected: 4.11.2
ocamlfind query zarith
```

The Rust side uses the same stable toolchain as the rest of this artifact:

```bash
rustup toolchain install stable
cargo +stable --version
rustc +stable --version
```

`make macro_sbpf` passes `OCAML_VERSION=4.11.2` and
`RUST_TOOLCHAIN=stable` by default. The Rust runner invokes Cargo with
`--locked`, removes `RUSTC_BOOTSTRAP` from the child environment, and sets
`RUSTFLAGS=-Awarnings`.

### 3.2 Quick start

The minimal set of commands required to execute the Isabelle2Rust workflow and reproduce the core results:

```bash
# Generate Rust code from tests_targted/List_Test theory and cargo run:
make test TEST_DIR=tests_targeted TEST_THEORY=List_Test

# Run the targeted tests benchmarks
make targeted

# Run the HOL codegenerator tests benchmarks
make hol

# Run the sBPF macro validation suite
make macro_sbpf

# More commands
make help
```

## 4. Step by Step Instructions

This section provides detailed instructions for generating Rust code from Isabelle theories and running the corresponding tests.

```bash
# to open Isabelle/jedit
make open

# to open one generated test session in Isabelle/jEdit
make open_test TEST_DIR=tests_targeted/types TEST_THEORY=Type_Tuple_Test
```

### 4.1 Code generation

To generate Rust code from a certain Isabelle theory, use:

```bash
make build TEST_DIR=<dir> TEST_THEORY=<thy>
# for example: make build TEST_DIR=tests_targeted TEST_THEORY=List_Test
```

This command performs the following:

- creates a temporary `test-root/ROOT` file,
- triggers the Rust backend and produces the corresponding Rust project under:

```bash
<TEST_DIR>/stage1/<TEST_THEORY>/export*/
```

To enable Rust code export, the Isabelle theory must contain an explicit `export_code` command, for example:

```isabelle
export_code <THOERY_NAME> in Rust
```

You can also view the generated Rust code in the output panel through `theory exports`.

### 4.2 Running generated Rust code

Each generated project follows a standard Cargo structure:

```css
export1/
  ├── Cargo.toml
  └── src/
      ├── main.rs
      ├── <module1>.rs
      ├── <module2>.rs
      └── ...
```

To generate and run the exported Rust code in one step, use:

```bash
make gen DIR=<dir> Name=<thy>
# for example: make gen DIR=tests_targeted/lists Name=List_Test
```

This builds the Isabelle theory and triggers `cargo run` on the generated project.

Please ensure that the Rust sources remain in their original locations under `stage1/<TEST_THEORY>/export*/`, as the build pipeline relies on this structure.

For convenience, you can run the entire workflow (build + execute)using:

```bash
make test TEST_DIR=<dir> TEST_THEORY=<thy>
# for example: make test TEST_DIR=tests_targeted TEST_THEORY=List_Test
```

### 4.3 Running the test suites

#### Target test suites

To run all 41 targeted test cases:

```bash
make targeted
# >>> [1] Abs_Addn_Test
# Running Rust ...
# Exporting Rust ...
# === cargo run: .../Abs_Addn_Test/export1/Cargo.toml ===
# Compiling ...
# Finished ...
# Running ...
```

Running all tests takes some time...

```bash
================================
Targeted summary:
  Passed: 41
  Failed: 0
  Total:  41
```

#### HOL Codegenerator tests

To run the 7 official HOL `codegenerator_tests`:

```bash
make hol
```

The `gcd`  Boolean expressions are combined using `and`, producing a single final Boolean value.

```rust
fn main(){
    println!("hol_test = {}", gcd_test())
}

// hol_test = true
```

A result of `true` indicates that all HOL tests pass successfully.

#### sBPF macro validation

The sBPF macro validation follows the program-level validation flow used by
CertSBF's `make macro-test`. The input suite is the Solana official program
test set already encoded in `tests_sbpf/tests/exec_semantics/sbpf_ocaml/test.ml`,
so this target does not generate random tests.

Fixed execution environment:

```bash
# OCaml execution path
ocamlc -version
# expected: 4.11.2
ocamlfind query zarith

# Rust execution path
cargo +stable --version
rustc +stable --version

# Isabelle generation path
isabelle version
# expected: Isabelle2025
```

Run the full macro validation from the repository root:

```bash
make macro_sbpf
```

The target follows this path strictly:

- Shared stage (`tests_sbpf/tests/exec_semantics/run_macro_sbpf.py`): ensures
  `bpf_generator.thy` has been exported by Isabelle and refreshes the shared
  local data file `tests_sbpf/tests/data/interp_in.json` from
  `tests_sbpf/tests/exec_semantics/sbpf_ocaml/test.ml` only when the cached
  source hash changes.
- OCaml stage (`tests_sbpf/tests/exec_semantics/sbpf_ocaml/`): reads the
  Isabelle-generated
  `tests_sbpf/theory/stage1/bpf_generator/interp_test.ocaml`, injects the OCaml
  conversion glue, compiles it with the local macro data in `sbpf_ocaml/test.ml`,
  and runs the 146 Solana macro cases. The compiled OCaml macro binary is cached
  and reused until the generated OCaml export, local macro data, glue version, or
  fixed OCaml version changes.
- Rust stage (`tests_sbpf/tests/exec_semantics/sbpf_rust/`): reads the
  Isabelle-generated `interp_test` Cargo project, installs the Rust glue harness
  `interp_main.rs`, reads `interp_in.json`, and runs the same 146 macro cases
  through Cargo. By default the Rust runner does not impose a per-case timeout;
  it prints each case before starting it and reports elapsed time after the case
  finishes, then lists the slowest Rust cases in the summary.

Useful options:

```bash
# Force Isabelle to regenerate the OCaml and Rust exports before running the macro suite
make macro_sbpf REBUILD=1

# Override the fixed versions only when intentionally changing the test setup
make macro_sbpf OCAML_VERSION=4.11.2 RUST_TOOLCHAIN=stable

# Rebuild only the cached shared JSON data
make macro_sbpf DATA_REBUILD=1

# Rebuild only the cached OCaml glue/binary
OCAML_REBUILD=1 make macro_sbpf

# Optional Rust diagnostic timeout, in seconds
RUST_CASE_TIMEOUT=30 make macro_sbpf
```

The command prints progress messages for both environments and ends with a
statistical summary, for example:

```text
macro_sbpf summary
  OCaml export: Passed 146 / Failed 0 / Total 146
  Rust export: Passed 146 / Failed 0 / Total 146
  Overall: PASS
```

The final status is `PASS` only when both the OCaml export run and the Rust
export run have zero failed cases.
