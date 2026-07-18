#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_root=$(cd -- "$repo_root/.." && pwd)

cd "$workspace_root"

{
  printf 'tool:isabelle=%s\0' "$(isabelle version)"
  printf 'tool:rustc=%s\0' "$(rustc --version)"
  printf 'tool:cargo=%s\0' "$(cargo --version)"

  find Isabelle2Rust -type f \
    \( -path 'Isabelle2Rust/code_rust.ML' \
       -o -path 'Isabelle2Rust/Rust_Setup.thy' \
       -o -path 'Isabelle2Rust/Rust_BigInt_Int_Setup.thy' \
       -o -path 'Isabelle2Rust/Rust_BigInt_Nat_Setup.thy' \
       -o -path 'Isabelle2Rust/Makefile' \
       -o -path 'Isabelle2Rust/ROOT' \
       -o -path 'Isabelle2Rust/scripts/isabelle-exported.Cargo.lock' \
       -o -path 'Isabelle2Rust/scripts/hol-experiment-fingerprint.sh' \
       -o -path 'Isabelle2Rust/test/HOL_Codegenerator/*.thy' \
       -o -path 'Isabelle2Rust/test/HOL_Codegenerator/template/*.rs' \
       -o -path 'Isabelle2Rust/optimize/Cargo.toml' \
       -o -path 'Isabelle2Rust/optimize/Cargo.lock' \
       -o -path 'Isabelle2Rust/optimize/src/*.rs' \
       -o -path 'Isabelle2Rust/optimize/src/bin/*.rs' \) \
    -print0

  find RustLightAST -type f \
    \( -path 'RustLightAST/Cargo.toml' \
       -o -path 'RustLightAST/Cargo.lock' \
       -o -path 'RustLightAST/src/*.rs' \) \
    -print0
} |
  if command -v sort >/dev/null 2>&1; then sort -z; else tee; fi |
  while IFS= read -r -d '' path; do
    if [[ "$path" == tool:* ]]; then
      printf '%s\n' "$path"
    elif [[ -f "$path" ]]; then
      printf '%s\0' "$path"
      sha256sum "$path"
    fi
  done |
  sha256sum |
  awk '{print $1}'
