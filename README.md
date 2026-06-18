# Isabelle2Rust Artifact (AE Branch)

This repository contains the **artifact evaluation (AE) version** of the Isabelle2Rust toolchain submitted to FM2026.

Active development of Isabelle2Rust continues on the **dev branch**.

The most recent updates can be found at:

👉 https://github.com/shenghaoyuan/Isabelle2Rust/tree/dev

## 1. Introduction

The repository consists of these major components:

- **`code_rust.ML`** : the core of the Isabelle2Rust backend, implemented in Poly/ML. Link to paper‘s Section3.
- **`Rust_Setup.thy`** : the code adaptation layer that contains lightweight mapping rules.
- **`tests_HOL/`** : a collection of 7 official `HOL codegenerator_tests`, evaluates to a Boolean result. Link to paper's Section 4.
- **`tests_targeted/`** : a suite of 41 targeted test cases designed to exercise representative translation scenarios. All tests compile and execute successfully via Cargo. Link to paper's Section 4.

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

#install nightly
rustup toolchain install nightly-2025-12-01
#go to our repo folder
cd /OUR-REPO
rustup override set nightly-2025-12-01
#check version
cargo --version && rustc --version
#expected：cargo 1.93.0-nightly (2a7c49606 2025-11-25)
#expected：rustc 1.93.0-nightly (b84478a1c 2025-11-30)
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

### 3.2 Quick start

The minimal set of commands required to execute the Isabelle2Rust workflow and reproduce the core results:

```bash
# Generate Rust code from tests_targted/List_Test theory and cargo run:
make test TEST_DIR=tests_targeted TEST_THEORY=List_Test

# Run the targeted tests benchmarks
make targeted

# Run the HOL codegenerator tests benchmarks
make hol

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
