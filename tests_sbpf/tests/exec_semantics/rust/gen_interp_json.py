#!/usr/bin/env python3
# Extract the 146 interpreter test cases from ../test.ml into a shared JSON file
# (tests_sbpf/tests/data/interp_in.json) consumed by the Rust cross-test harness
# (interp_main.rs).  test.ml is the single source of truth: it holds the
# Solana-derived cases that the OCaml reference (Interp_test.bpf_interp_test)
# already validates, so the JSON carries the known-correct expected values.
#
# Each emitted record:
#   {dis, lp_std:[i64], lm_std:[i64], lc_std:[i64], v:i64, fuel:i64,
#    result_expected:i64, isok:bool}
# OCaml int64 literals (decimal `180L`, hex `0xaaL`) are evaluated and wrapped to
# signed 64-bit, matching OCaml `int64` semantics (e.g. 0xFFFFFFFFFFFFFFFFL -> -1).

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_ML = os.path.normpath(os.path.join(HERE, "..", "test.ml"))
OUT_JSON = os.path.normpath(
    os.path.join(HERE, "..", "..", "data", "interp_in.json")
)


def strip_ocaml_comments(src):
    """Remove (* ... *) comments (nesting-aware), preserving string literals.

    This also drops records that are commented out in test.ml so they are not
    mistaken for live cases."""
    out = []
    i, n = 0, len(src)
    depth = 0
    in_str = False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if depth > 0:
            if c == "(" and i + 1 < n and src[i + 1] == "*":
                depth += 1
                i += 2
                continue
            if c == "*" and i + 1 < n and src[i + 1] == ")":
                depth -= 1
                i += 2
                continue
            i += 1
            continue
        # not in string, not in comment
        if c == "(" and i + 1 < n and src[i + 1] == "*":
            depth += 1
            i += 2
            continue
        if c == '"':
            in_str = True
        out.append(c)
        i += 1
    return "".join(out)


def to_i64(literal):
    """Evaluate an OCaml int64 literal (with trailing L) into a signed 64-bit int."""
    s = literal.strip()
    if s.endswith("L") or s.endswith("l"):
        s = s[:-1]
    v = int(s, 0) & ((1 << 64) - 1)
    if v >= (1 << 63):
        v -= 1 << 64
    return v


def parse_int_list(body):
    body = body.strip()
    if not body:
        return []
    return [to_i64(tok) for tok in body.split(";") if tok.strip()]


def find_list(record, field):
    m = re.search(re.escape(field) + r"\s*=\s*\[([^\]]*)\]", record)
    if not m:
        raise ValueError("missing list field %s in record: %s" % (field, record[:80]))
    return parse_int_list(m.group(1))


def find_scalar(record, field):
    m = re.search(re.escape(field) + r"\s*=\s*([^;]+);", record)
    if not m:
        raise ValueError("missing field %s in record: %s" % (field, record[:80]))
    return m.group(1).strip()


def main():
    with open(TEST_ML, "r", encoding="utf-8") as f:
        src = f.read()
    src = strip_ocaml_comments(src)

    start = src.index("test_cases")
    start = src.index("[", start)
    # match the closing bracket of the list
    depth = 0
    end = None
    for i in range(start, len(src)):
        if src[i] == "[":
            depth += 1
        elif src[i] == "]":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise ValueError("could not find end of test_cases list")
    block = src[start + 1:end]

    cases = []
    for m in re.finditer(r"\{(.*?)\}", block, re.DOTALL):
        rec = m.group(1)
        dis = re.search(r'dis\s*=\s*"((?:[^"\\]|\\.)*)"', rec)
        if not dis:
            raise ValueError("record without dis: %s" % rec[:80])
        cases.append({
            "dis": dis.group(1),
            "lp_std": find_list(rec, "lp_std"),
            "lm_std": find_list(rec, "lm_std"),
            "lc_std": find_list(rec, "lc_std"),
            "v": to_i64(find_scalar(rec, "v")),
            "fuel": to_i64(find_scalar(rec, "fuel")),
            "result_expected": to_i64(find_scalar(rec, "result_expected")),
            "isok": find_scalar(rec, "isok") == "true",
        })

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
        f.write("\n")
    print("wrote %d cases to %s" % (len(cases), OUT_JSON))


if __name__ == "__main__":
    sys.exit(main())
