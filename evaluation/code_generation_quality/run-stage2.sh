#!/usr/bin/env bash
set -uo pipefail

unset RUSTC_BOOTSTRAP

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
targeted="$repo_root/tests_targeted"
optimizer="$repo_root/optimize/Cargo.toml"
lock_template="$repo_root/scripts/isabelle-exported.Cargo.lock"
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
  root=""
  for candidate in "${roots[@]}"; do
    if [[ "$project_dir" == "$candidate"/stage1/* ]]; then
      root="$candidate"
      break
    fi
  done

  if [[ -z "$root" ]]; then
    printf 'FAIL\t%s\tunable to determine test root\n' "$project_dir"
    failed=$((failed + 1))
    continue
  fi

  relative="${project_dir#"$root/stage1/"}"
  output="$root/stage2/$relative"
  printf '[%d/%d] %s\n' "$((passed + failed + 1))" "$total" "$relative"
  rm -rf "$output"

  if ! cargo +"$toolchain" run -q --manifest-path "$optimizer" \
      --bin cargo-opt -- \
      "$project_dir" --out-dir "$output"; then
    printf 'FAIL\t%s\toptimization\n' "$relative"
    failed=$((failed + 1))
    continue
  fi

  if [[ ! -f "$output/Cargo.lock" ]]; then
    if [[ -f "$project_dir/Cargo.lock" ]]; then
      cp "$project_dir/Cargo.lock" "$output/Cargo.lock"
    elif [[ -f "$lock_template" ]]; then
      cp "$lock_template" "$output/Cargo.lock"
    fi
  fi

  if RUSTFLAGS="-Awarnings" cargo +"$toolchain" build --locked \
      --manifest-path "$output/Cargo.toml" >/dev/null; then
    printf 'PASS\t%s\n' "$relative"
    passed=$((passed + 1))
  else
    printf 'FAIL\t%s\tcargo build\n' "$relative"
    failed=$((failed + 1))
  fi
done

printf 'Stage-2 summary: passed=%d failed=%d total=%d toolchain=%s\n' \
  "$passed" "$failed" "$total" "$toolchain"

if ((failed > 0)); then
  exit 1
fi
