#!/usr/bin/env bash
set -uo pipefail

unset RUSTC_BOOTSTRAP

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
targeted="$repo_root/tests_targeted"
toolchain="${RUST_TOOLCHAIN:-stable}"
unit_groups=(abstraction cases classes constructors functions lets lists records types)
roots=()

for group in "${unit_groups[@]}"; do
  roots+=("$targeted/$group")
done
roots+=("$targeted/fpp")

mapfile -t manifests < <(
  find "${roots[@]}" -path '*/stage1/*/export*/Cargo.toml' -type f | sort
)

passed=0
failed=0
total="${#manifests[@]}"

for manifest in "${manifests[@]}"; do
  project_dir="$(dirname "$manifest")"
  relative="${project_dir#"$targeted/"}"
  printf '[%d/%d] %s\n' "$((passed + failed + 1))" "$total" "$relative"

  if RUSTFLAGS="-Awarnings" cargo +"$toolchain" build --locked \
      --manifest-path "$manifest" >/dev/null; then
    printf 'PASS\t%s\n' "$relative"
    passed=$((passed + 1))
  else
    printf 'FAIL\t%s\n' "$relative"
    failed=$((failed + 1))
  fi
done

printf 'Stage-1 summary: passed=%d failed=%d total=%d toolchain=%s\n' \
  "$passed" "$failed" "$total" "$toolchain"

if ((failed > 0)); then
  exit 1
fi
