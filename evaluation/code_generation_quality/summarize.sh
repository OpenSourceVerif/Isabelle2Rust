#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
targeted="$repo_root/tests_targeted"
unit_groups=(abstraction cases classes constructors functions lets lists records types)

unit_theories=0
for group in "${unit_groups[@]}"; do
  n="$(find "$targeted/$group" -maxdepth 1 -name '*_Test.thy' -type f | wc -l)"
  unit_theories=$((unit_theories + n))
done

fpp_theories="$(find "$targeted/fpp" -name '*_Test.thy' -type f | wc -l)"
fpp_export_theories=0
expected_theories=()
while IFS= read -r theory; do
  if rg -q '^export_code' "$theory"; then
    fpp_export_theories=$((fpp_export_theories + 1))
    expected_theories+=("$theory")
  fi
done < <(find "$targeted/fpp" -name '*_Test.thy' -type f | sort)

for group in "${unit_groups[@]}"; do
  while IFS= read -r theory; do
    expected_theories+=("$theory")
  done < <(find "$targeted/$group" -maxdepth 1 -name '*_Test.thy' -type f | sort)
done

missing_stage1=0
for theory in "${expected_theories[@]}"; do
  directory="$(dirname "$theory")"
  name="$(basename "$theory" .thy)"
  if ! find "$directory/stage1/$name" -path '*/export*/Cargo.toml' \
      -type f -print -quit 2>/dev/null | rg -q .; then
    printf 'Missing Stage-1 output: %s\n' "${theory#"$repo_root/"}" >&2
    missing_stage1=$((missing_stage1 + 1))
  fi
done

collect_roots=()
for group in "${unit_groups[@]}"; do
  collect_roots+=("$targeted/$group")
done
collect_roots+=("$targeted/fpp")

stage1_projects="$(find "${collect_roots[@]}" -path '*/stage1/*/export*/Cargo.toml' -type f | wc -l)"
stage2_projects="$(
  find "${collect_roots[@]}" \
    \( -path '*/stage2/*/Cargo.toml' -o -path '*/stage2/*/export*/Cargo.toml' \) \
    -type f | wc -l
)"
stage1_theories="$(
  find "${collect_roots[@]}" -path '*/stage1/*/export*/Cargo.toml' -type f |
    sed -E 's#^(.*)/stage1/([^/]+)/.*#\1/stage1/\2#' | sort -u | wc -l
)"
stage2_theories="$(
  find "${collect_roots[@]}" \
      \( -path '*/stage2/*/Cargo.toml' -o -path '*/stage2/*/export*/Cargo.toml' \) \
      -type f |
    sed -E 's#^(.*)/stage2/([^/]+)/.*#\1/stage2/\2#' | sort -u | wc -l
)"
stage1_loc="$(find "${collect_roots[@]}" -path '*/stage1/*/export*/src/*.rs' -type f -print0 |
  xargs -0 -r wc -l | awk 'END {print $1 + 0}')"
stage2_loc="$(find "${collect_roots[@]}" \
    \( -path '*/stage2/*/src/*.rs' -o -path '*/stage2/*/export*/src/*.rs' \) \
    -type f -print0 |
  xargs -0 -r wc -l | awk 'END {print $1 + 0}')"

unsafe_hits="$({
  find "${collect_roots[@]}" \
    \( -path '*/stage1/*/export*/src/*.rs' -o \
       -path '*/stage2/*/src/*.rs' -o \
       -path '*/stage2/*/export*/src/*.rs' \) \
    -type f -print0 |
    xargs -0 -r rg -n '\bunsafe\b' 2>/dev/null || true
} | wc -l)"

printf 'Unit-test theories:            %s\n' "$unit_theories"
printf 'FPP theories:                  %s\n' "$fpp_theories"
printf 'FPP theories with exports:     %s\n' "$fpp_export_theories"
printf 'Common comparison corpus:      %s\n' "$((unit_theories + fpp_export_theories))"
printf 'Missing Stage-1 theories:      %s\n' "$missing_stage1"
printf 'Generated Stage-1 theories:    %s\n' "$stage1_theories"
printf 'Generated Stage-2 theories:    %s\n' "$stage2_theories"
printf 'Generated Stage-1 projects:    %s\n' "$stage1_projects"
printf 'Generated Stage-2 projects:    %s\n' "$stage2_projects"
printf 'Generated Stage-1 Rust LOC:    %s\n' "$stage1_loc"
printf 'Generated Stage-2 Rust LOC:    %s\n' "$stage2_loc"
printf 'Generated unsafe occurrences: %s\n' "$unsafe_hits"
