#!/usr/bin/env python3
"""Assemble the independently produced RQ1 measurements into table rows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


SUITES = ("HCT-standard", "HCT-binary-nat", "Unit", "FPP")
EXPECTED_PAIRS = {"HCT-standard": 1, "HCT-binary-nat": 1, "Unit": 53, "FPP": 36}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def indexed(rows: list[dict[str, str]], key) -> dict[object, dict[str, str]]:
    answer = {}
    for row in rows:
        item = key(row)
        if item in answer:
            raise RuntimeError(f"duplicate input row for {item}")
        answer[item] = row
    return answer


def reduction(stage1: int, stage2: int) -> str:
    return f"{100.0 * (stage1 - stage2) / stage1:.1f}"


def assemble(
    acceptance_path: Path, loc_path: Path, timings_path: Path
) -> list[dict[str, str]]:
    acceptance = indexed(
        [row for row in read_csv(acceptance_path) if row["suite"] != "Total"],
        lambda row: row["suite"],
    )
    loc = indexed(
        read_csv(loc_path),
        lambda row: (row["suite"], row["stage"]),
    )
    timings = indexed(
        [row for row in read_csv(timings_path) if row["suite"] != "Cumulative total"],
        lambda row: row["suite"],
    )

    rows = []
    for suite in SUITES:
        if suite not in acceptance or suite not in timings:
            raise RuntimeError(f"missing acceptance or timing row for {suite}")
        for stage in ("stage1", "stage2"):
            if (suite, stage) not in loc:
                raise RuntimeError(f"missing generated-LOC row for {suite} {stage}")

        accepted = acceptance[suite]
        pairs = int(accepted["pairs"])
        stage1_accepted = int(accepted["stage1_accepted"])
        stage2_accepted = int(accepted["stage2_accepted"])
        if (pairs, stage1_accepted, stage2_accepted) != (
            EXPECTED_PAIRS[suite],
            EXPECTED_PAIRS[suite],
            EXPECTED_PAIRS[suite],
        ):
            raise RuntimeError(f"incomplete compiler acceptance for {suite}: {accepted}")

        stage1_loc = int(loc[(suite, "stage1")]["rust_loc"])
        stage2_loc = int(loc[(suite, "stage2")]["rust_loc"])
        timing = timings[suite]
        if not timing["translation_seconds"] or not timing["optimization_seconds"]:
            raise RuntimeError(f"incomplete timing row for {suite}: {timing}")
        rows.append(
            {
                "suite": suite,
                "stage1_accepted": str(stage1_accepted),
                "stage2_accepted": str(stage2_accepted),
                "stage1_rust_loc": str(stage1_loc),
                "stage2_rust_loc": str(stage2_loc),
                "reduction_percent": reduction(stage1_loc, stage2_loc),
                "translation_seconds": f'{float(timing["translation_seconds"]):.2f}',
                "optimization_seconds": f'{float(timing["optimization_seconds"]):.2f}',
            }
        )

    stage1_loc = sum(int(row["stage1_rust_loc"]) for row in rows)
    stage2_loc = sum(int(row["stage2_rust_loc"]) for row in rows)
    rows.append(
        {
            "suite": "Cumulative total",
            "stage1_accepted": str(sum(int(row["stage1_accepted"]) for row in rows)),
            "stage2_accepted": str(sum(int(row["stage2_accepted"]) for row in rows)),
            "stage1_rust_loc": str(stage1_loc),
            "stage2_rust_loc": str(stage2_loc),
            "reduction_percent": reduction(stage1_loc, stage2_loc),
            "translation_seconds": f'{sum(float(row["translation_seconds"]) for row in rows):.2f}',
            "optimization_seconds": f'{sum(float(row["optimization_seconds"]) for row in rows):.2f}',
        }
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = []
    for row in rows:
        lines.append(
            "{} & {}/{} & {:.3f} & {:.3f} & {}\\% & {} & {} \\\\".format(
                row["suite"],
                row["stage1_accepted"],
                row["stage2_accepted"],
                int(row["stage1_rust_loc"]) / 1000,
                int(row["stage2_rust_loc"]) / 1000,
                row["reduction_percent"],
                row["translation_seconds"],
                row["optimization_seconds"],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", required=True, type=Path)
    parser.add_argument("--loc", required=True, type=Path)
    parser.add_argument("--timings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--latex-output", type=Path)
    args = parser.parse_args()
    try:
        rows = assemble(args.acceptance, args.loc, args.timings)
        write_csv(args.output, rows)
        if args.latex_output:
            write_latex(args.latex_output, rows)
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
