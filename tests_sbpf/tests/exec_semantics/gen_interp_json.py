#!/usr/bin/env python3
"""Extract macro interpreter cases from sbpf_ocaml/test.ml into data/interp_in.json."""

import json
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
TEST_ML = os.path.join(HERE, "sbpf_ocaml", "test.ml")
OUT_JSON = os.path.normpath(os.path.join(HERE, "..", "data", "interp_in.json"))


def strip_ocaml_comments(src):
    """Remove nested OCaml comments while preserving string literals."""
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
    s = literal.strip()
    if s.endswith("L") or s.endswith("l"):
        s = s[:-1]
    value = int(s, 0) & ((1 << 64) - 1)
    if value >= (1 << 63):
        value -= 1 << 64
    return value


def parse_int_list(body):
    body = body.strip()
    if not body:
        return []
    return [to_i64(tok) for tok in body.split(";") if tok.strip()]


def find_list(record, field):
    match = re.search(re.escape(field) + r"\s*=\s*\[([^\]]*)\]", record)
    if not match:
        raise ValueError("missing list field %s in record: %s" % (field, record[:80]))
    return parse_int_list(match.group(1))


def find_scalar(record, field):
    match = re.search(re.escape(field) + r"\s*=\s*([^;]+);", record)
    if not match:
        raise ValueError("missing field %s in record: %s" % (field, record[:80]))
    return match.group(1).strip()


def main():
    with open(TEST_ML, "r", encoding="utf-8") as f:
        src = strip_ocaml_comments(f.read())

    start = src.index("test_cases")
    start = src.index("[", start)
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

    cases = []
    block = src[start + 1:end]
    for match in re.finditer(r"\{(.*?)\}", block, re.DOTALL):
        record = match.group(1)
        dis = re.search(r'dis\s*=\s*"((?:[^"\\]|\\.)*)"', record)
        if not dis:
            raise ValueError("record without dis: %s" % record[:80])
        cases.append({
            "dis": dis.group(1),
            "lp_std": find_list(record, "lp_std"),
            "lm_std": find_list(record, "lm_std"),
            "lc_std": find_list(record, "lc_std"),
            "v": to_i64(find_scalar(record, "v")),
            "fuel": to_i64(find_scalar(record, "fuel")),
            "result_expected": to_i64(find_scalar(record, "result_expected")),
            "isok": find_scalar(record, "isok") == "true",
        })

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
        f.write("\n")
    print("wrote %d cases to %s" % (len(cases), OUT_JSON))


if __name__ == "__main__":
    sys.exit(main())
