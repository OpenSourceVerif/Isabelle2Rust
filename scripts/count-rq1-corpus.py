#!/usr/bin/env python3
"""Count the theories and definition selections in the RQ1 corpus."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
COUNTER = REPO / "scripts/count-rust-export-items.pl"
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
HCT_STATS = re.compile(
    r"HOL_STRESS_STATS theory=(Generate(?:_Binary_Nat)?) "
    r"entry_points=(\d+) definitions=(\d+)"
)


def tracked_theories(suite: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", f"test/{suite}"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )
    theories = []
    for relative in result.stdout.splitlines():
        if relative.startswith("test/unit/example/"):
            continue
        path = REPO / relative
        if (
            path.is_file()
            and path.name.endswith("_Test.thy")
            and EXPORT_CODE.search(path.read_text(encoding="utf-8"))
        ):
            theories.append(path)
    return sorted(theories)


def explicit_selections(theory: Path) -> int:
    return int(
        subprocess.check_output(
            ["perl", str(COUNTER), str(theory)], cwd=REPO, text=True
        ).strip()
    )


def hct_counts(logs: list[Path]) -> dict[str, tuple[int, int]]:
    counts = {}
    for log in logs:
        for theory, entry_points, definitions in HCT_STATS.findall(
            log.read_text(encoding="utf-8", errors="replace")
        ):
            counts[theory] = (int(entry_points), int(definitions))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hct-log",
        action="append",
        default=[],
        type=Path,
        help="Isabelle build log containing HOL_STRESS_STATS (repeatable)",
    )
    parser.add_argument("--output", type=Path, help="write CSV instead of stdout")
    args = parser.parse_args()

    hct = hct_counts(args.hct_log)
    unit = tracked_theories("unit")
    fpp = tracked_theories("fpp")
    rows = [
        {
            "suite": "HCT-standard",
            "theories": 1,
            "definition_selections": hct.get("Generate", ("", ""))[0],
            "thingol_function_nodes": hct.get("Generate", ("", ""))[1],
            "source": "HOL_STRESS_STATS" if "Generate" in hct else "requires --hct-log",
        },
        {
            "suite": "HCT-binary-nat",
            "theories": 1,
            "definition_selections": hct.get("Generate_Binary_Nat", ("", ""))[0],
            "thingol_function_nodes": hct.get("Generate_Binary_Nat", ("", ""))[1],
            "source": "HOL_STRESS_STATS" if "Generate_Binary_Nat" in hct else "requires --hct-log",
        },
        {
            "suite": "Unit",
            "theories": len(unit),
            "definition_selections": sum(map(explicit_selections, unit)),
            "thingol_function_nodes": "",
            "source": "explicit export_code selections",
        },
        {
            "suite": "FPP",
            "theories": len(fpp),
            "definition_selections": sum(map(explicit_selections, fpp)),
            "thingol_function_nodes": "",
            "source": "explicit export_code selections",
        },
    ]
    fields = list(rows[0])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        target = args.output.open("w", newline="", encoding="utf-8")
    else:
        target = sys.stdout
    try:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            target.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
