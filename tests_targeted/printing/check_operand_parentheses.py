#!/usr/bin/env python3
"""Check Stage 1 grouping after exporting the two operand test theories.

Usage: python3 check_operand_parentheses.py Conditional_Operand_Test.rs CaseOperand.rs
The assertions ignore whitespace and generated local names. Cargo/runtime checks
cover semantics; these checks also reject unnecessary grouping in safe positions.
"""

import argparse
from pathlib import Path
import re


def function_body(source: str, name: str) -> str:
    header = re.search(rf"\bpub\s+fn\s+{re.escape(name)}\b[^{{]*\{{", source)
    if header is None:
        raise ValueError(f"missing function {name}")
    # Skip quoted strings so their braces cannot end a generated function.
    depth = 1
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]', source[header.end():]):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                body = source[header.end():header.end() + token.start()]
                return re.sub(r"\s+", "", body)
    raise ValueError(f"unterminated function {name}")


CONDITIONAL_CHECKS = [
    ("conditional_tail", r"^if", "tail if has no outer parentheses"),
    ("conditional_tail", r"\{if", "nested tail if has no outer parentheses"),
    ("conditional_sum", r"^\(if.*\}\)\+\(if", "both arithmetic operands are grouped"),
    ("conditional_product", r"^\(if.*\}\)\*", "left multiplicand is grouped"),
    ("conditional_compare", r"^\(if.*\}\)<", "comparison operand is grouped"),
    ("conditional_compare", r"\{if", "nested comparison branch needs no grouping"),
    ("conditional_and", r"^\(if.*\}\)&&", "left boolean operand is grouped"),
    ("conditional_or", r"\|\|\(if", "right boolean operand is grouped"),
    ("conditional_argument", r"conditional_sum\(if", "function argument needs no grouping"),
    ("conditional_condition", r"^ifif", "if condition needs no grouping"),
    ("conditional_opaque", r"^\(if.*\}\)&&true$", "opaque NOBR slot keeps grouping"),
]

CASE_CHECKS = [
    ("case_tail", r"^match", "tail match has no outer parentheses"),
    ("case_and", r"^\(match.*\}\)&&", "left match operand is grouped"),
    ("case_or", r"^\(match.*\}\)\|\|", "match disjunction operand is grouped"),
    ("case_right", r"&&\(match", "right match operand is grouped"),
    ("case_argument", r",match", "match argument needs no grouping"),
    ("case_condition", r"^ifmatch", "match condition needs no grouping"),
    ("case_callee", r"^\(\*\(match", "computed match callee is grouped"),
    ("case_arithmetic", r"^\(match.*\}\)\+", "arithmetic match operand is grouped"),
    ("case_binding", r"^\(\{let.*\}\)&&", "binding block operand is grouped"),
    ("case_binding_tail", r"^let", "tail bindings need no extra block or parentheses"),
    ("case_binding_argument", r",\{let", "binding block argument needs no grouping"),
    ("case_binding_condition", r"^if\{let", "binding block condition needs no grouping"),
    ("case_tree", r"^\(match.*\}\)&&", "staged match operand is grouped"),
    ("case_tree", r"=>match", "nested staged match tails need no grouping"),
    ("case_boxed_if", r"Box::new\(if", "boxed if needs no additional parentheses"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conditional", type=Path)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    failures = []
    for path, checks in [(args.conditional, CONDITIONAL_CHECKS), (args.case, CASE_CHECKS)]:
        source = path.read_text()
        for function, pattern, description in checks:
            try:
                if re.search(pattern, function_body(source, function)) is None:
                    failures.append(f"{function}: {description}")
            except ValueError as error:
                failures.append(str(error))
    if failures:
        raise SystemExit("Parenthesis checks failed:\n" + "\n".join(failures))
    print(f"Passed {len(CONDITIONAL_CHECKS) + len(CASE_CHECKS)} parenthesis checks.")


if __name__ == "__main__":
    main()
