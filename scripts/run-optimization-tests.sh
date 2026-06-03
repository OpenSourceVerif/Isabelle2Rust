#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPTIMIZE_DIR="$ROOT_DIR/optimize"
STAGE="${1:-copy}"
THEORY="Copy_Inference_Test"
TEST_DIR="tests_targeted/optimization/copy"
BASE_DIR="$ROOT_DIR/$TEST_DIR/Rust_Out/$THEORY/export1"
OUT_ROOT="$OPTIMIZE_DIR/tests/out"
OPT_DIR="$OUT_ROOT/copy/$THEORY/opt"
BASE_RS="$BASE_DIR/src/$THEORY.rs"
BASE_LOCK="$BASE_DIR/Cargo.lock"
OPT_RS="$OPT_DIR/src/$THEORY.rs"
OPT_PRODUCT_RS="$OPT_DIR/src/Product_Type.rs"

TESTS=0
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

usage() {
  cat <<'EOF_USAGE'
usage: scripts/run-optimization-tests.sh [copy|borrow|copy-borrow|all]

Stages:
  copy         Run copy inference tests.
  borrow       Reserved for borrow optimization tests.
  copy-borrow  Reserved for composed copy + borrow optimization tests.
  all          Run every configured optimization stage.
EOF_USAGE
}

pass() {
  TESTS=$((TESTS + 1))
  printf 'ok %02d - %s\n' "$TESTS" "$1"
}

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if grep -Fq "$pattern" "$file"; then
    pass "$label"
  else
    fail "$label: missing pattern '$pattern' in $file"
  fi
}

assert_not_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if grep -Fq "$pattern" "$file"; then
    fail "$label: unexpected pattern '$pattern' in $file"
  else
    pass "$label"
  fi
}

assert_count_eq() {
  local file="$1"
  local pattern="$2"
  local expected="$3"
  local label="$4"
  local count
  count="$(grep -Fc "$pattern" "$file" || true)"
  if [ "$count" -eq "$expected" ]; then
    pass "$label"
  else
    fail "$label: expected $expected occurrences of '$pattern' in $file, got $count"
  fi
}

function_body_file() {
  local name="$1"
  local output="$TMP_DIR/$name.rs"
  awk -v name="$name" '
    BEGIN { needle = "pub fn " name }
    index($0, needle) == 1 {
      if (capture) { exit }
      capture = 1
    }
    capture && /^pub fn / && index($0, needle) != 1 { exit }
    capture { print }
  ' "$OPT_RS" > "$output"

  if grep -Fq "pub fn $name" "$output"; then
    printf '%s\n' "$output"
  else
    fail "function $name exists in optimized output"
  fi
}

assert_fn_contains() {
  local name="$1"
  local pattern="$2"
  local label="$3"
  local body
  body="$(function_body_file "$name")"
  assert_contains "$body" "$pattern" "$label"
}

assert_fn_not_contains() {
  local name="$1"
  local pattern="$2"
  local label="$3"
  local body
  body="$(function_body_file "$name")"
  assert_not_contains "$body" "$pattern" "$label"
}

case "$STAGE" in
  all)
    "$0" copy
    exit 0
    ;;
  copy)
    ;;
  borrow|copy-borrow)
    printf 'stage "%s" has no configured tests yet\n' "$STAGE"
    exit 0
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if command -v flock >/dev/null 2>&1; then
  exec 9>"$ROOT_DIR/.optimization-test.lock"
  flock 9
fi

printf '>>> [%s] generating baseline Rust from Isabelle theory %s\n' "$STAGE" "$THEORY"
make -C "$ROOT_DIR" -s build_silent TEST_DIR="$TEST_DIR" TEST_THEORY="$THEORY"
test -f "$BASE_RS" || fail "baseline Rust source was generated"
pass "Isabelle generated baseline Rust"

printf '>>> compiling baseline Cargo project\n'
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --manifest-path "$BASE_DIR/Cargo.toml" >/dev/null
pass "baseline Rust project compiles and runs"
test -f "$BASE_LOCK" || fail "baseline Cargo.lock was generated"

printf '>>> optimizing baseline Rust project\n'
rm -rf "$OPT_DIR"
cargo run -q --manifest-path "$OPTIMIZE_DIR/Cargo.toml" --bin cargo-opt -- \
  "$BASE_DIR" --out-dir "$OPT_DIR" >/dev/null
test -f "$OPT_RS" || fail "optimized Rust source was generated"
pass "optimizer produced rewritten Rust"

printf '>>> compiling optimized Cargo project\n'
cp "$BASE_LOCK" "$OPT_DIR/Cargo.lock"
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --locked --manifest-path "$OPT_DIR/Cargo.toml" >/dev/null
pass "optimized Rust project compiles and runs"

BASE_CLONES="$(grep -Fc ".clone()" "$BASE_RS" || true)"
OPT_CLONES="$(grep -Fc ".clone()" "$OPT_RS" || true)"
if [ "$OPT_CLONES" -lt "$BASE_CLONES" ]; then
  pass "optimizer reduces clone calls ($BASE_CLONES -> $OPT_CLONES)"
else
  fail "optimizer should reduce clone calls, got $BASE_CLONES -> $OPT_CLONES"
fi

assert_count_eq "$OPT_RS" "#[derive(Clone, Copy)]" 9 "nine generated local datatypes derive Copy"
assert_count_eq "$OPT_RS" "#[derive(Clone)]" 1 "recursive CopyTree stays Clone-only"
assert_count_eq "$OPT_PRODUCT_RS" "#[derive(Clone, Copy)]" 1 "generated Prod datatype derives Copy"
assert_contains "$OPT_RS" "CopyNode(Box<CopyTree>, Box<CopyTree>)" "recursive datatype keeps Box fields"
assert_contains "$OPT_RS" "pub enum NestedCopyWrap <A>" "nested generic wrapper datatype is generated"

assert_contains "$OPT_RS" "pub fn wrap_dup_copy<A>" "copy-specialized wrap_dup is emitted"
assert_contains "$OPT_RS" "pub fn value_dup_copy<A>" "copy-specialized value_dup is emitted"
assert_contains "$OPT_RS" "pub fn pair_wrap_dup_copy<A, B>" "copy-specialized pair_wrap_dup is emitted"
assert_contains "$OPT_RS" "pub fn pair_wrap_swap_copy<A, B>" "copy-specialized pair_wrap_swap is emitted"
assert_contains "$OPT_RS" "pub fn pair_wrap_first_copy<A, B>" "copy-specialized pair_wrap_first is emitted"
assert_contains "$OPT_RS" "pub fn wrap_unwrap_copy<A>" "copy-specialized wrap_unwrap is emitted"
assert_contains "$OPT_RS" "pub fn nested_wrap_dup_copy<A>" "copy-specialized nested_wrap_dup is emitted"
assert_not_contains "$OPT_RS" "pub fn wrap_tree_dup_copy" "concrete non-Copy wrapper does not get a copy specialization"

assert_fn_not_contains "flag_dup" ".clone()" "flag_dup has no clone calls"
assert_fn_contains "flag_dup" "Prod::Pair(x, x)" "flag_dup reuses Copy value directly"
assert_fn_not_contains "flag_swap" ".clone()" "flag_swap has no clone calls"
assert_fn_contains "flag_swap" "FlagPair::FlagPair(y, x)" "flag_swap rewrites constructor arguments"
assert_fn_not_contains "triple_rotate" ".clone()" "triple_rotate has no clone calls"
assert_fn_contains "triple_rotate" "FlagTriple::FlagTriple(y, z, x)" "triple_rotate rewrites all fields"
assert_fn_not_contains "color_dup" ".clone()" "color_dup has no clone calls"
assert_fn_contains "color_dup" "Prod::Pair(c, c)" "color_dup reuses enum value directly"
assert_fn_not_contains "pixel_rotate" ".clone()" "pixel_rotate has no clone calls"
assert_fn_contains "pixel_rotate" "Pixel::Pixel(g, b, r)" "pixel_rotate rewrites nested Copy fields"
assert_fn_not_contains "pixel_replace_first" ".clone()" "pixel_replace_first has no clone calls"
assert_fn_contains "pixel_replace_first" "Pixel::Pixel(c, g, b)" "tuple-pattern field types are recovered"
assert_fn_not_contains "nested_dup" ".clone()" "nested_dup has no clone calls"
assert_fn_contains "nested_dup" "Prod::Pair(x, x)" "nested datatype duplication uses Copy"
assert_fn_not_contains "palette_swap" ".clone()" "palette_swap has no clone calls"
assert_fn_contains "palette_swap" "Palette::Palette(q, p)" "copyability propagates through datatype dependencies"
assert_fn_not_contains "wrap_map_flag" ".clone()" "concrete generic wrapper field clone is removed"
assert_fn_contains "wrap_map_flag" "x" "concrete wrapper returns its Copy field directly"

assert_fn_not_contains "wrap_dup_copy" ".clone()" "wrap_dup_copy has no clone calls"
assert_fn_contains "wrap_dup_copy" "where A: Copy" "wrap_dup_copy strengthens A to Copy"
assert_fn_contains "wrap_dup_copy" "Prod::Pair(x, x)" "wrap_dup_copy reuses wrapped value directly"
assert_fn_not_contains "value_dup_copy" ".clone()" "value_dup_copy has no clone calls"
assert_fn_contains "value_dup_copy" "where A: Copy" "value_dup_copy strengthens A to Copy"
assert_fn_not_contains "pair_wrap_dup_copy" ".clone()" "pair_wrap_dup_copy has no clone calls"
assert_fn_contains "pair_wrap_dup_copy" "where A: Copy, B: Copy" "pair_wrap_dup_copy strengthens both parameters"
assert_fn_not_contains "pair_wrap_swap_copy" ".clone()" "pair_wrap_swap_copy has no clone calls"
assert_fn_contains "pair_wrap_swap_copy" "CopyPairWrap::CopyPairWrap(y, x)" "pair_wrap_swap_copy rewrites both field clones"
assert_fn_not_contains "pair_wrap_first_copy" ".clone()" "pair_wrap_first_copy has no clone calls"
assert_fn_contains "pair_wrap_first_copy" "where A: Copy" "pair_wrap_first_copy strengthens only demanded parameter"
assert_fn_not_contains "wrap_unwrap_copy" ".clone()" "wrap_unwrap_copy has no clone calls"

assert_fn_not_contains "nested_wrap_dup_copy" ".clone()" "nested_wrap_dup_copy has no clone calls"
assert_fn_contains "nested_wrap_dup_copy" "where A: Copy" "nested_wrap_dup_copy strengthens nested parameter"
assert_fn_contains "nested_wrap_dup_copy" "Prod::Pair(x, x)" "nested wrapper duplication uses Copy when A is Copy"
assert_fn_not_contains "nested_wrap_unwrap_flag" ".clone()" "concrete nested wrapper unwrap removes Copy field clone"
assert_fn_contains "nested_wrap_unwrap_flag" "x" "concrete nested wrapper returns Copy field directly"
assert_fn_contains "wrap_tree_dup" "x.clone()" "CopyWrap<CopyTree> keeps clone because concrete argument is not Copy"
assert_fn_not_contains "mixed_pair_first" ".clone()" "Copy field inside non-Copy pair wrapper is still copied directly"
assert_fn_contains "mixed_pair_first" "x" "mixed_pair_first returns the Copy field"
assert_fn_contains "mixed_pair_dup" "x.clone()" "whole mixed pair wrapper keeps clone because one field is non-Copy"

assert_fn_contains "tree_dup" "x.clone()" "recursive Box datatype keeps necessary clone"
assert_fn_contains "wrap_dup" "where A: Clone" "original generic wrap_dup remains Clone-compatible"
assert_fn_contains "wrap_dup" "x.clone()" "original generic wrap_dup preserves clone path"
assert_fn_contains "value_dup" "where A: Clone" "original generic value_dup remains Clone-compatible"
assert_fn_contains "pair_wrap_swap" "where A: Clone, B: Clone" "original pair_wrap_swap remains Clone-compatible"

if [ "$TESTS" -ge 20 ]; then
  printf 'copy inference regression suite passed: %d checks\n' "$TESTS"
else
  fail "expected at least 20 checks, ran $TESTS"
fi
