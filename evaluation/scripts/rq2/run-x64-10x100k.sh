#!/usr/bin/env bash
set -euo pipefail

# Run the canonical x86-64 differential validation in independent batches.
#
# Default campaign: 10 batches * 100,000 vectors = 1,000,000 vectors.
# The canonical `make x64` workflow checks the raw Rust encoder against OCaml,
# then checks the OCaml and raw Rust steppers against native x86-64 execution.
#
# Optional environment overrides:
#   ROUNDS=10
#   CASES_PER_ROUND=100000
#   PREPARE_EXPORTS=1      # 1 (force), auto (if missing), or 0 (reuse only)
#   ARCHIVE_CORPUS=1       # archive each batch's step1--step4 files
#   RESULT_DIR=/path/to/results

if [[ ${1:-} == "--help" ]]; then
  sed -n '4,15p' "$0"
  exit 0
elif (($# != 0)); then
  printf 'usage: %s [--help]\n' "$0" >&2
  exit 2
fi

script_path=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
data_dir="$repo_root/tests_x64/x64-validation/0-data"
encoder_export="$repo_root/tests_x64/theory/stage1/x64EncodeRustGenerator/x64_encode"
stepper_export="$repo_root/tests_x64/theory/stage1/x64StepRustGenerator/x64_step_test"

rounds=${ROUNDS:-10}
cases_per_round=${CASES_PER_ROUND:-100000}
prepare_exports=${PREPARE_EXPORTS:-1}
archive_corpus=${ARCHIVE_CORPUS:-1}
timestamp=$(date +%Y%m%d-%H%M%S)
result_dir=${RESULT_DIR:-$repo_root/evaluation/results/rq2/x64-${rounds}x${cases_per_round}-${timestamp}}
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
if [[ $prepare_exports != auto && $prepare_exports != 0 && $prepare_exports != 1 ]]; then
  printf 'ERROR: PREPARE_EXPORTS must be auto, 0, or 1, got %q\n' "$prepare_exports" >&2
  exit 2
fi
if [[ $archive_corpus != 0 && $archive_corpus != 1 ]]; then
  printf 'ERROR: ARCHIVE_CORPUS must be 0 or 1, got %q\n' "$archive_corpus" >&2
  exit 2
fi
if [[ $(uname -m) != x86_64 ]]; then
  printf 'ERROR: native x86-64 validation requires an x86_64 host.\n' >&2
  exit 2
fi
for tool in awk find flock git grep make sha256sum sort tee; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "$tool" >&2
    exit 2
  fi
done
if [[ $archive_corpus == 1 ]] && ! command -v tar >/dev/null 2>&1; then
  printf 'ERROR: ARCHIVE_CORPUS=1 requires tar.\n' >&2
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
printf 'round\tcases\tstep1_sha256\tstep2_sha256\tstep3_sha256\tstep4_sha256\tcorpus_archive\n' >"$summary_tsv"

{
  printf 'campaign=x64 differential validation\n'
  printf 'started_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'rounds=%s\n' "$rounds"
  printf 'cases_per_round=%s\n' "$cases_per_round"
  printf 'total_vectors=%s\n' "$((rounds * cases_per_round))"
  printf 'prepare_exports=%s\n' "$prepare_exports"
  printf 'archive_corpus=%s\n' "$archive_corpus"
  printf 'rust_scope=canonical raw Stage-1 encoder and stepper exports\n'
  printf 'rust_toolchain=stable\n'
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
  -u CC
  -u OCAMLC
  -u OCAMLFIND
  -u REBUILD
  -u RUSTC_BOOTSTRAP
  -u RUSTFLAGS
  -u RUST_TOOLCHAIN
  -u X64_COUNT
  -u X64_JANSSON_LIBS
  -u X64_OCAML_PACKAGES
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
        /Rust encoder cross-check:/ ||
        /Complete test cases generated/ ||
        /Summary:/ ||
        /Rust semantics vs CPU:/ {
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

encoder_manifest="$encoder_export/Cargo.toml"
stepper_manifest="$stepper_export/Cargo.toml"
need_prepare=0
if [[ $prepare_exports == 1 ]]; then
  need_prepare=1
elif [[ $prepare_exports == auto ]] && { [[ ! -f $encoder_manifest ]] || [[ ! -f $stepper_manifest ]]; }; then
  need_prepare=1
fi
if [[ $need_prepare == 1 ]]; then
  printf 'Preparing current canonical x86-64 Rust exports.\n'
  run_logged "$result_dir/prepare-exports.log" \
    "${clean_env[@]}" make x64-rust-export REBUILD=1
fi
for manifest in "$encoder_manifest" "$stepper_manifest"; do
  if [[ ! -f $manifest ]]; then
    printf 'ERROR: required x86-64 export is missing: %s\n' "$manifest" >&2
    printf 'Set PREPARE_EXPORTS=1 to regenerate the canonical exports.\n' >&2
    exit 2
  fi
done
{
  printf 'encoder_export_sha256=%s\n' "$(sha256_tree "$encoder_export")"
  printf 'stepper_export_sha256=%s\n' "$(sha256_tree "$stepper_export")"
} >>"$result_dir/metadata.txt"

declare -A seen_step4_hashes=()
for ((round = 1; round <= rounds; round++)); do
  round_id=$(printf '%02d' "$round")
  log_file="$result_dir/round-${round_id}.log"
  printf '\n=== x64 round %d/%d: %d vectors ===\n' "$round" "$rounds" "$cases_per_round"
  printf 'Full log: %s\n' "$log_file"

  run_logged "$log_file" \
    "${clean_env[@]}" make x64 X64_COUNT="$cases_per_round"

  grep -Fq "Rust encoder cross-check: $cases_per_round passed / 0 failed" "$log_file" || {
    printf 'ERROR: missing successful Rust encoder summary in %s\n' "$log_file" >&2
    exit 1
  }
  grep -Eq "Summary: .*${cases_per_round} passed.* / .*0 failed" "$log_file" || {
    printf 'ERROR: missing successful OCaml semantics summary in %s\n' "$log_file" >&2
    exit 1
  }
  grep -Fq "Rust semantics vs CPU: $cases_per_round passed / 0 failed (0 panicked)" "$log_file" || {
    printf 'ERROR: missing successful Rust semantics summary in %s\n' "$log_file" >&2
    exit 1
  }

  for data_file in step1.in step2.in step3.json step4.json; do
    if [[ ! -s $data_dir/$data_file ]]; then
      printf 'ERROR: expected x64 corpus file is missing or empty: %s\n' "$data_dir/$data_file" >&2
      exit 1
    fi
  done
  observed_cases=$(grep -c '^[[:space:]]*"ins"[[:space:]]*:' "$data_dir/step4.json")
  if [[ $observed_cases != "$cases_per_round" ]]; then
    printf 'ERROR: step4.json contains %s cases; expected %s\n' "$observed_cases" "$cases_per_round" >&2
    exit 1
  fi

  step1_sha=$(sha256_file "$data_dir/step1.in")
  step2_sha=$(sha256_file "$data_dir/step2.in")
  step3_sha=$(sha256_file "$data_dir/step3.json")
  step4_sha=$(sha256_file "$data_dir/step4.json")
  if [[ ${seen_step4_hashes[$step4_sha]+present} ]]; then
    printf 'ERROR: round %d reproduced an earlier step4 corpus (%s).\n' "$round" "$step4_sha" >&2
    exit 1
  fi
  seen_step4_hashes[$step4_sha]=$round

  archive_name='not-archived'
  if [[ $archive_corpus == 1 ]]; then
    archive_name="round-${round_id}-corpus.tar.gz"
    printf 'Archiving batch corpus as %s\n' "$result_dir/$archive_name"
    tar -czf "$result_dir/$archive_name" -C "$data_dir" \
      step1.in step2.in step3.json step4.json
  fi

  printf '%d\t%d\t%s\t%s\t%s\t%s\t%s\n' \
    "$round" "$cases_per_round" "$step1_sha" "$step2_sha" \
    "$step3_sha" "$step4_sha" "$archive_name" >>"$summary_tsv"
done

total_vectors=$((rounds * cases_per_round))
{
  printf 'status=PASS\n'
  printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'rounds=%d\n' "$rounds"
  printf 'cases_per_round=%d\n' "$cases_per_round"
  printf 'total_test_vectors=%d\n' "$total_vectors"
  printf 'rust_encoder_failed=0\n'
  printf 'ocaml_stepper_failed=0\n'
  printf 'rust_stepper_failed=0\n'
} >"$result_dir/summary.txt"

printf '\nPASS: %d x86-64 vectors validated in %d independent batches.\n' "$total_vectors" "$rounds"
printf 'Results: %s\n' "$result_dir"
