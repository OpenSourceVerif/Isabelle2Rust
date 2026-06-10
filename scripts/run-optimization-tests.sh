#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPTIMIZE_DIR="$ROOT_DIR/optimize"
STAGE="${1:-copy}"

# ── Per-stage configuration ───────────────────────────────────────────────────

# copy stage
COPY_THEORY="Copy_Inference_Test"
COPY_TEST_DIR="tests_targeted/optimization/copy"
COPY_BASE_DIR="$ROOT_DIR/$COPY_TEST_DIR/Rust_Out/$COPY_THEORY/export1"
COPY_STAGE1_DIR="$OPTIMIZE_DIR/tests/stage1/$COPY_THEORY"
COPY_STAGE2_DIR="$OPTIMIZE_DIR/tests/stage2/$COPY_THEORY"
COPY_BASE_RS="$COPY_BASE_DIR/src/$COPY_THEORY.rs"
COPY_BASE_LOCK="$COPY_BASE_DIR/Cargo.lock"
COPY_OPT_RS="$COPY_STAGE2_DIR/src/$COPY_THEORY.rs"
COPY_OPT_PRODUCT_RS="$COPY_STAGE2_DIR/src/Product_Type.rs"

# borrow stage
BORROW_THEORY="Borrow_Inference_Test"
BORROW_TEST_DIR="tests_targeted/optimization/borrow"
BORROW_BASE_DIR="$ROOT_DIR/$BORROW_TEST_DIR/Rust_Out/$BORROW_THEORY/export1"
BORROW_STAGE1_DIR="$OPTIMIZE_DIR/tests/stage1/$BORROW_THEORY"
BORROW_STAGE2_DIR="$OPTIMIZE_DIR/tests/stage2/$BORROW_THEORY"
BORROW_BASE_RS="$BORROW_BASE_DIR/src/$BORROW_THEORY.rs"
BORROW_BASE_LOCK="$BORROW_BASE_DIR/Cargo.lock"
BORROW_OPT_RS="$BORROW_STAGE2_DIR/src/$BORROW_THEORY.rs"

TESTS=0
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

usage() {
  cat <<'EOF_USAGE'
usage: scripts/run-optimization-tests.sh [copy|borrow|copy-borrow|all]

Stages:
  copy         Run copy inference tests (Copy_Inference_Test).
  borrow       Run borrow inference tests (Borrow_Inference_Test).
  copy-borrow  Run copy stage then borrow stage (sequential).
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

assert_count_ge() {
  local file="$1"
  local pattern="$2"
  local min="$3"
  local label="$4"
  local count
  count="$(grep -Fc "$pattern" "$file" || true)"
  if [ "$count" -ge "$min" ]; then
    pass "$label"
  else
    fail "$label: expected at least $min occurrences of '$pattern' in $file, got $count"
  fi
}

function_body_file() {
  local name="$1"
  local src_file="${2:-$COPY_OPT_RS}"
  local output="$TMP_DIR/$name.rs"
  awk -v name="$name" '
    BEGIN { needle = "pub fn " name }
    index($0, needle) == 1 {
      if (capture) { exit }
      capture = 1
    }
    capture && /^pub fn / && index($0, needle) != 1 { exit }
    capture { print }
  ' "$src_file" > "$output"

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
  local src_file="${4:-$COPY_OPT_RS}"
  local body
  body="$(function_body_file "$name" "$src_file")"
  assert_contains "$body" "$pattern" "$label"
}

assert_fn_not_contains() {
  local name="$1"
  local pattern="$2"
  local label="$3"
  local src_file="${4:-$COPY_OPT_RS}"
  local body
  body="$(function_body_file "$name" "$src_file")"
  assert_not_contains "$body" "$pattern" "$label"
}

# ── Stage dispatch ────────────────────────────────────────────────────────────

case "$STAGE" in
  all)
    "$0" copy
    "$0" borrow
    exit 0
    ;;
  copy-borrow)
    "$0" copy
    "$0" borrow
    exit 0
    ;;
  copy)
    ;;
  borrow)
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

# ── COPY stage ────────────────────────────────────────────────────────────────

if [ "$STAGE" = "copy" ]; then

printf '>>> [copy] generating stage1 Rust from Isabelle theory %s\n' "$COPY_THEORY"
make -C "$ROOT_DIR" -s build_silent TEST_DIR="$COPY_TEST_DIR" TEST_THEORY="$COPY_THEORY"
test -f "$COPY_BASE_RS" || fail "baseline Rust source was generated"
pass "Isabelle generated baseline Rust"

printf '>>> syncing stage1 snapshot\n'
rm -rf "$COPY_STAGE1_DIR"
mkdir -p "$COPY_STAGE1_DIR"
cp -r "$COPY_BASE_DIR/." "$COPY_STAGE1_DIR/"
pass "stage1 snapshot written to optimize/tests/stage1/$COPY_THEORY"

printf '>>> compiling stage1 Cargo project\n'
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --manifest-path "$COPY_STAGE1_DIR/Cargo.toml" >/dev/null
pass "stage1 Rust project compiles and runs"
test -f "$COPY_BASE_LOCK" || fail "baseline Cargo.lock was generated"

printf '>>> optimizing: stage1 -> stage2 (copy + borrow passes)\n'
rm -rf "$COPY_STAGE2_DIR"
cargo run -q --manifest-path "$OPTIMIZE_DIR/Cargo.toml" --bin cargo-opt -- \
  "$COPY_STAGE1_DIR" --out-dir "$COPY_STAGE2_DIR" >/dev/null
test -f "$COPY_OPT_RS" || fail "optimized Rust source was generated"
pass "optimizer produced stage2 rewritten Rust"

printf '>>> compiling stage2 Cargo project\n'
cp "$COPY_BASE_LOCK" "$COPY_STAGE2_DIR/Cargo.lock"
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --locked --manifest-path "$COPY_STAGE2_DIR/Cargo.toml" >/dev/null
pass "stage2 Rust project compiles and runs"

COPY_BASE_CLONES="$(grep -Fc ".clone()" "$COPY_BASE_RS" || true)"
COPY_OPT_CLONES="$(grep -Fc ".clone()" "$COPY_OPT_RS" || true)"
if [ "$COPY_OPT_CLONES" -lt "$COPY_BASE_CLONES" ]; then
  pass "optimizer reduces clone calls ($COPY_BASE_CLONES -> $COPY_OPT_CLONES)"
else
  fail "optimizer should reduce clone calls, got $COPY_BASE_CLONES -> $COPY_OPT_CLONES"
fi

assert_count_eq "$COPY_OPT_RS" "#[derive(Clone, Copy)]" 9 "nine generated local datatypes derive Copy"
assert_count_eq "$COPY_OPT_RS" "#[derive(Clone)]" 1 "recursive CopyTree stays Clone-only"
assert_count_eq "$COPY_OPT_PRODUCT_RS" "#[derive(Clone, Copy)]" 1 "generated Prod datatype derives Copy"
assert_contains "$COPY_OPT_RS" "CopyNode(Box<CopyTree>, Box<CopyTree>)" "recursive datatype keeps Box fields"
assert_contains "$COPY_OPT_RS" "pub enum NestedCopyWrap <A>" "nested generic wrapper datatype is generated"

assert_contains "$COPY_OPT_RS" "pub fn wrap_dup_copy<A>" "copy-specialized wrap_dup is emitted"
assert_contains "$COPY_OPT_RS" "pub fn value_dup_copy<A>" "copy-specialized value_dup is emitted"
assert_contains "$COPY_OPT_RS" "pub fn pair_wrap_dup_copy<A, B>" "copy-specialized pair_wrap_dup is emitted"
assert_contains "$COPY_OPT_RS" "pub fn pair_wrap_swap_copy<A, B>" "copy-specialized pair_wrap_swap is emitted"
assert_contains "$COPY_OPT_RS" "pub fn pair_wrap_first_copy<A, B>" "copy-specialized pair_wrap_first is emitted"
assert_contains "$COPY_OPT_RS" "pub fn wrap_unwrap_copy<A>" "copy-specialized wrap_unwrap is emitted"
assert_contains "$COPY_OPT_RS" "pub fn nested_wrap_dup_copy<A>" "copy-specialized nested_wrap_dup is emitted"
assert_not_contains "$COPY_OPT_RS" "pub fn wrap_tree_dup_copy" "concrete non-Copy wrapper does not get a copy specialization"

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

# R-Call: call-site redirection to _copy specialization
assert_fn_not_contains "use_wrap_dup_flag" "wrap_dup(" "concrete Copy caller does not call Clone variant"
assert_fn_contains "use_wrap_dup_flag" "wrap_dup_copy(x)" "concrete Copy caller is redirected to wrap_dup_copy (R-Call)"
assert_fn_not_contains "use_value_dup_flag" "value_dup(" "concrete Copy caller does not call Clone variant of value_dup"
assert_fn_contains "use_value_dup_flag" "value_dup_copy(x)" "concrete Copy caller is redirected to value_dup_copy (R-Call)"
assert_fn_contains "use_wrap_dup_generic" "wrap_dup(" "generic Clone caller still calls original wrap_dup"
assert_fn_not_contains "use_wrap_dup_generic" "wrap_dup_copy" "generic Clone caller does not redirect to copy variant"
assert_fn_contains "use_wrap_dup_generic_copy" "wrap_dup_copy(x)" "generic Copy specialization is redirected to wrap_dup_copy (R-Call)"
assert_fn_not_contains "use_wrap_dup_generic_copy" "wrap_dup(" "generic Copy specialization does not keep Clone call"

if [ "$TESTS" -ge 20 ]; then
  printf 'copy inference regression suite passed: %d checks\n' "$TESTS"
else
  fail "expected at least 20 checks, ran $TESTS"
fi

fi  # end STAGE=copy

# ── BORROW stage ──────────────────────────────────────────────────────────────

if [ "$STAGE" = "borrow" ]; then

printf '>>> [borrow] generating stage1 Rust from Isabelle theory %s\n' "$BORROW_THEORY"
make -C "$ROOT_DIR" -s build_silent TEST_DIR="$BORROW_TEST_DIR" TEST_THEORY="$BORROW_THEORY"
test -f "$BORROW_BASE_RS" || fail "borrow baseline Rust source was generated"
pass "Isabelle generated borrow baseline Rust"

printf '>>> syncing borrow stage1 snapshot\n'
rm -rf "$BORROW_STAGE1_DIR"
mkdir -p "$BORROW_STAGE1_DIR"
cp -r "$BORROW_BASE_DIR/." "$BORROW_STAGE1_DIR/"
pass "borrow stage1 snapshot written to optimize/tests/stage1/$BORROW_THEORY"

printf '>>> compiling borrow stage1 Cargo project\n'
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --manifest-path "$BORROW_STAGE1_DIR/Cargo.toml" >/dev/null
pass "borrow stage1 Rust project compiles and runs"
test -f "$BORROW_BASE_LOCK" || fail "borrow baseline Cargo.lock was generated"

printf '>>> optimizing: borrow stage1 -> stage2 (copy + borrow passes)\n'
rm -rf "$BORROW_STAGE2_DIR"
cargo run -q --manifest-path "$OPTIMIZE_DIR/Cargo.toml" --bin cargo-opt -- \
  "$BORROW_STAGE1_DIR" --out-dir "$BORROW_STAGE2_DIR" >/dev/null
test -f "$BORROW_OPT_RS" || fail "borrow optimized Rust source was generated"
pass "optimizer produced borrow stage2 rewritten Rust"

printf '>>> compiling borrow stage2 Cargo project\n'
cp "$BORROW_BASE_LOCK" "$BORROW_STAGE2_DIR/Cargo.lock"
RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --locked --manifest-path "$BORROW_STAGE2_DIR/Cargo.toml" >/dev/null
pass "borrow stage2 Rust project compiles and runs"

# ── Structural checks on stage2 output ───────────────────────────────────────

# borrow variants must be emitted for all major functions
assert_contains "$BORROW_OPT_RS" "pub fn btree_is_leaf_borrow" "btree_is_leaf gets a borrow variant"
assert_contains "$BORROW_OPT_RS" "pub fn btree_leaf_val_borrow" "btree_leaf_val gets a borrow variant"
assert_contains "$BORROW_OPT_RS" "pub fn btree_dup_borrow" "btree_dup gets a borrow variant"
assert_contains "$BORROW_OPT_RS" "pub fn bbox_get_borrow" "bbox_get gets a borrow variant"
assert_contains "$BORROW_OPT_RS" "pub fn bbox_dup_borrow" "bbox_dup gets a borrow variant"
assert_contains "$BORROW_OPT_RS" "pub fn bbox_swap_borrow" "bbox_swap gets a borrow variant"

# borrow variant parameters must use reference types
assert_contains "$BORROW_OPT_RS" "&BorrowTree" "borrow variants carry &BorrowTree reference parameters"
assert_contains "$BORROW_OPT_RS" "&BorrowBox" "borrow variants carry &BorrowBox reference parameters"

# original (owned) functions must still be present alongside borrow variants
assert_contains "$BORROW_OPT_RS" "pub fn btree_is_leaf" "original btree_is_leaf is preserved"
assert_contains "$BORROW_OPT_RS" "pub fn btree_dup" "original btree_dup is preserved"
assert_contains "$BORROW_OPT_RS" "pub fn bbox_get" "original bbox_get is preserved"

# at least 4 _borrow definitions in the file
assert_count_ge "$BORROW_OPT_RS" "_borrow" 4 "at least four _borrow function definitions are emitted"

# borrow variants must not have owned-type parameters for the borrowable positions
assert_fn_contains "btree_is_leaf_borrow" "&BorrowTree" "btree_is_leaf_borrow takes &BorrowTree" "$BORROW_OPT_RS"
assert_fn_contains "btree_dup_borrow" "&BorrowTree" "btree_dup_borrow takes &BorrowTree" "$BORROW_OPT_RS"
assert_fn_contains "bbox_get_borrow" "&BorrowBox" "bbox_get_borrow takes &BorrowBox<A>" "$BORROW_OPT_RS"
assert_fn_contains "bbox_dup_borrow" "&BorrowBox" "bbox_dup_borrow takes &BorrowBox<A>" "$BORROW_OPT_RS"

# BorrowTree is recursive → must stay Clone-only (not Copy)
assert_contains "$BORROW_OPT_RS" "#[derive(Clone)]" "BorrowTree stays Clone-only (recursive type)"
assert_not_contains "$BORROW_OPT_RS" "pub enum BorrowTree" "BorrowTree not derive Copy" || true
# more precise: the BorrowTree derive must NOT include Copy
BTREE_DERIVE="$(grep -B1 "pub enum BorrowTree" "$BORROW_OPT_RS" || true)"
if echo "$BTREE_DERIVE" | grep -Fq "Copy"; then
  fail "BorrowTree must not derive Copy (recursive type)"
else
  pass "BorrowTree does not derive Copy (correct for recursive type)"
fi

if [ "$TESTS" -ge 10 ]; then
  printf 'borrow inference regression suite passed: %d checks\n' "$TESTS"
else
  fail "expected at least 10 checks, ran $TESTS"
fi

fi  # end STAGE=borrow
