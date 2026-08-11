#!/usr/bin/env bash
set -euo pipefail

# Run the SBPF instruction-level differential validation in independent batches.
#
# Default campaign: 10 batches * 100,000 vectors = 1,000,000 vectors.
# Each batch uses a distinct recorded seed and checks the OCaml, Stage-1 Rust,
# and full Stage-2 Rust exports. The generated corpus is retained and compressed.
#
# Optional environment overrides:
#   ROUNDS=10
#   CASES_PER_ROUND=100000
#   SEED_BASE=5984326
#   PREPARE_EXPORTS=1      # 1 (force), auto (if missing), or 0 (reuse only)
#   COMPRESS_CORPUS=1
#   RESULT_DIR=/path/to/results

if [[ ${1:-} == "--help" ]]; then
  sed -n '4,16p' "$0"
  exit 0
elif (($# != 0)); then
  printf 'usage: %s [--help]\n' "$0" >&2
  exit 2
fi

script_path=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
theory_dir="$repo_root/tests_sbpf/theory"
stage1_export="$theory_dir/stage1/bpf_generator"
stage2_export="$theory_dir/stage2/bpf_generator"
stage2_runner="$repo_root/tests_sbpf/tests/exec_semantics/sbpf_rust/run_step_micro.py"

rounds=${ROUNDS:-10}
cases_per_round=${CASES_PER_ROUND:-100000}
seed_base=${SEED_BASE:-5984326}
prepare_exports=${PREPARE_EXPORTS:-1}
compress_corpus=${COMPRESS_CORPUS:-1}
timestamp=$(date +%Y%m%d-%H%M%S)
result_dir=${RESULT_DIR:-$repo_root/evaluation/performance/results/rq2-sbpf-${rounds}x${cases_per_round}-${timestamp}}
if [[ $result_dir != /* ]]; then
  result_dir="$repo_root/$result_dir"
fi

require_positive_integer() {
  local name=$1 value=$2
  if [[ ! $value =~ ^[1-9][0-9]*$ ]]; then
    printf 'ERROR: %s must be a positive integer, got %q\n' "$name" "$value" >&2
    exit 2
  fi
}

require_positive_integer ROUNDS "$rounds"
require_positive_integer CASES_PER_ROUND "$cases_per_round"
if [[ ! $seed_base =~ ^[0-9]+$ ]]; then
  printf 'ERROR: SEED_BASE must be a non-negative integer, got %q\n' "$seed_base" >&2
  exit 2
fi
if [[ $prepare_exports != auto && $prepare_exports != 0 && $prepare_exports != 1 ]]; then
  printf 'ERROR: PREPARE_EXPORTS must be auto, 0, or 1, got %q\n' "$prepare_exports" >&2
  exit 2
fi
if [[ $compress_corpus != 0 && $compress_corpus != 1 ]]; then
  printf 'ERROR: COMPRESS_CORPUS must be 0 or 1, got %q\n' "$compress_corpus" >&2
  exit 2
fi
for tool in awk find flock git grep make python3 sha256sum sort tee; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "$tool" >&2
    exit 2
  fi
done
if [[ $compress_corpus == 1 ]] && ! command -v gzip >/dev/null 2>&1; then
  printf 'ERROR: COMPRESS_CORPUS=1 requires gzip.\n' >&2
  exit 2
fi
if [[ -e $result_dir ]]; then
  printf 'ERROR: result directory already exists: %s\n' "$result_dir" >&2
  exit 2
fi

lock_id=$(printf '%s' "$repo_root" | sha256sum | awk '{print substr($1, 1, 16)}')
lock_file="/tmp/isabelle2rust-rq2-${lock_id}.lock"
exec 9>"$lock_file"
if ! flock -n 9; then
  printf 'ERROR: another RQ2 validation campaign holds %s\n' "$lock_file" >&2
  exit 2
fi

mkdir -p "$result_dir"
summary_tsv="$result_dir/batches.tsv"
printf 'round\tseed\tcases\tcorpus_sha256\tstage1_ocaml_failed\tstage1_rust_failed\tstage2_rust_failed\tcorpus_file\n' >"$summary_tsv"

{
  printf 'campaign=SBPF instruction-level differential validation\n'
  printf 'started_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'rounds=%s\n' "$rounds"
  printf 'cases_per_round=%s\n' "$cases_per_round"
  printf 'total_vectors=%s\n' "$((rounds * cases_per_round))"
  printf 'seed_base=%s\n' "$seed_base"
  printf 'prepare_exports=%s\n' "$prepare_exports"
  printf 'compress_corpus=%s\n' "$compress_corpus"
  printf 'numeric_profile=default BigInt export\n'
  printf 'rust_toolchain=stable\n'
  printf 'ocaml_version=4.11.2\n'
  printf 'campaign_lock=%s\n' "$lock_file"
  printf 'script=%s\n' "$script_path"
  printf 'script_sha256=%s\n' "$(sha256sum "$script_path" | awk '{print $1}')"
  printf 'git_commit=%s\n' "$(git -C "$repo_root" rev-parse HEAD)"
  printf 'uname=%s\n' "$(uname -a)"
  printf 'git_status_begin\n'
  git -C "$repo_root" status --short
  printf 'git_status_end\n'
} >"$result_dir/metadata.txt"

clean_env=(
  env
  -u CARGO
  -u CARGO_PROFILE_DEV_OPT_LEVEL
  -u OCAML_REBUILD
  -u OCAML_VERSION
  -u REBUILD
  -u RUSTC_BOOTSTRAP
  -u RUSTFLAGS
  -u RUST_TOOLCHAIN
  -u SBPF_EXPORT_DIR
  -u SBPF_NATIVE_INT
  -u SBPF_NO_BIGINT
  -u SBPF_STAGE
  -u SBPF_STEP_JSON
  -u SBPF_STEP_SEED
  -u SBPF_THEORY
  -u X
  -u num
)

run_logged() {
  local log_file=$1
  shift
  local -a status

  {
    printf 'command:'
    printf ' %q' "$@"
    printf '\n'
  } >"$log_file"
  set +e
  (
    cd "$repo_root"
    "$@"
  ) 2>&1 \
    | tee -a "$log_file" \
    | awk '
        /^>>>/ ||
        /Successfully generated/ ||
        /summary/ ||
        /Summary/ ||
        /Passed:/ ||
        /Failed:/ ||
        /Overall:/ {
          print
          fflush()
        }
      '
  status=("${PIPESTATUS[@]}")
  set -e

  if ((status[0] != 0 || status[1] != 0 || status[2] != 0)); then
    printf 'ERROR: command failed; tail of %s follows.\n' "$log_file" >&2
    tail -n 80 "$log_file" >&2
    return 1
  fi
}

stage1_manifest="$stage1_export/step_test/Cargo.toml"
stage2_manifest="$stage2_export/step_test/Cargo.toml"
need_prepare=0
if [[ $prepare_exports == 1 ]]; then
  need_prepare=1
elif [[ $prepare_exports == auto ]] && { [[ ! -f $stage1_manifest ]] || [[ ! -f $stage2_manifest ]]; }; then
  need_prepare=1
fi

if [[ $need_prepare == 1 ]]; then
  printf 'Preparing current Stage-1 and full Stage-2 SBPF exports.\n'
  run_logged "$result_dir/prepare-stage1.log" \
    "${clean_env[@]}" make gen DIR=tests_sbpf/theory Name=bpf_generator
  run_logged "$result_dir/prepare-stage2.log" \
    "${clean_env[@]}" make opt DIR=tests_sbpf/theory Name=bpf_generator
fi
for manifest in "$stage1_manifest" "$stage2_manifest"; do
  if [[ ! -f $manifest ]]; then
    printf 'ERROR: required SBPF export is missing: %s\n' "$manifest" >&2
    printf 'Set PREPARE_EXPORTS=1 to regenerate Stage-1 and Stage-2.\n' >&2
    exit 2
  fi
done
if [[ ! -f $stage2_runner ]]; then
  printf 'ERROR: Stage-2 runner is missing: %s\n' "$stage2_runner" >&2
  exit 2
fi

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

sha256_tree() {
  local tree=$1
  (
    cd "$tree"
    find . -type f ! -path './target/*' -print0 \
      | sort -z \
      | while IFS= read -r -d '' source; do
          printf '%s\0' "$source"
          sha256sum "$source"
        done
  ) | sha256sum | awk '{print $1}'
}

{
  printf 'stage1_export_sha256=%s\n' "$(sha256_tree "$stage1_export")"
  printf 'stage2_full_export_sha256=%s\n' "$(sha256_tree "$stage2_export")"
} >>"$result_dir/metadata.txt"

declare -A seen_corpus_hashes=()
for ((round = 1; round <= rounds; round++)); do
  round_id=$(printf '%02d' "$round")
  seed=$((seed_base + round - 1))
  corpus="$result_dir/round-${round_id}-seed-${seed}.json"
  generate_log="$result_dir/round-${round_id}-generate.log"
  stage1_log="$result_dir/round-${round_id}-stage1.log"
  stage2_log="$result_dir/round-${round_id}-stage2.log"

  printf '\n=== SBPF round %d/%d: %d vectors, seed %d ===\n' \
    "$round" "$rounds" "$cases_per_round" "$seed"

  run_logged "$generate_log" \
    "${clean_env[@]}" make micro_sbpf_gen \
      X="$cases_per_round" SBPF_STEP_SEED="$seed" SBPF_STEP_JSON="$corpus"
  grep -Fq "Successfully generated $cases_per_round random test cases with seed $seed" "$generate_log" || {
    printf 'ERROR: generator did not confirm the requested count and seed.\n' >&2
    exit 1
  }

  observed_cases=$(grep -c '^[[:space:]]*"dis"[[:space:]]*:' "$corpus")
  if [[ $observed_cases != "$cases_per_round" ]]; then
    printf 'ERROR: corpus contains %s cases; expected %s\n' "$observed_cases" "$cases_per_round" >&2
    exit 1
  fi

  run_logged "$stage1_log" \
    "${clean_env[@]}" make micro_sbpf \
      SBPF_EXPORT_DIR="$stage1_export" SBPF_STEP_JSON="$corpus"
  grep -Fq "OCaml export: Passed $cases_per_round / Failed 0 / Total $cases_per_round" "$stage1_log" || {
    printf 'ERROR: missing successful Stage-1 OCaml summary in %s\n' "$stage1_log" >&2
    exit 1
  }
  grep -Fq "Rust export: Passed $cases_per_round / Failed 0 / Total $cases_per_round" "$stage1_log" || {
    printf 'ERROR: missing successful Stage-1 Rust summary in %s\n' "$stage1_log" >&2
    exit 1
  }

  run_logged "$stage2_log" \
    "${clean_env[@]}" SBPF_STAGE=2 \
      SBPF_ROOT="$repo_root" \
      SBPF_EXEC_DIR="$repo_root/tests_sbpf/tests/exec_semantics" \
      SBPF_DATA_DIR="$repo_root/tests_sbpf/tests/data" \
      SBPF_EXPORT_DIR="$stage2_export" \
      SBPF_STEP_JSON="$corpus" \
      python3 "$stage2_runner"
  grep -Fq "Passed: $cases_per_round" "$stage2_log" || {
    printf 'ERROR: missing successful Stage-2 Rust passed count in %s\n' "$stage2_log" >&2
    exit 1
  }
  grep -Eq 'Failed:[[:space:]]*0([[:space:]]|$)' "$stage2_log" || {
    printf 'ERROR: missing zero-failure Stage-2 Rust summary in %s\n' "$stage2_log" >&2
    exit 1
  }

  corpus_sha=$(sha256_file "$corpus")
  if [[ ${seen_corpus_hashes[$corpus_sha]+present} ]]; then
    printf 'ERROR: round %d reproduced an earlier corpus (%s).\n' "$round" "$corpus_sha" >&2
    exit 1
  fi
  seen_corpus_hashes[$corpus_sha]=$round

  corpus_name=$(basename "$corpus")
  if [[ $compress_corpus == 1 ]]; then
    printf 'Compressing retained corpus %s\n' "$corpus"
    gzip -n "$corpus"
    corpus_name="${corpus_name}.gz"
  fi

  printf '%d\t%d\t%d\t%s\t0\t0\t0\t%s\n' \
    "$round" "$seed" "$cases_per_round" "$corpus_sha" "$corpus_name" >>"$summary_tsv"
done

total_vectors=$((rounds * cases_per_round))
{
  printf 'status=PASS\n'
  printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'rounds=%d\n' "$rounds"
  printf 'cases_per_round=%d\n' "$cases_per_round"
  printf 'total_test_vectors=%d\n' "$total_vectors"
  printf 'ocaml_failed=0\n'
  printf 'stage1_rust_failed=0\n'
  printf 'stage2_full_rust_failed=0\n'
} >"$result_dir/summary.txt"

printf '\nPASS: %d SBPF vectors validated in %d independent seeded batches.\n' "$total_vectors" "$rounds"
printf 'Results: %s\n' "$result_dir"
