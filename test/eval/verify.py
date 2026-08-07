#!/usr/bin/env python3
"""Verify the complete RQ3 paper-data provenance chain."""

from __future__ import annotations

import argparse
import csv
import hashlib
import statistics
from collections import Counter
from decimal import Decimal
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAPER = HERE.parents[2] / "TOSEM" / "latex" / "63rq3.tex"

IMPLEMENTATIONS = [
    "Stage-1",
    "Stage-2 minus Borrow",
    "Stage-2 minus Last-Use",
    "Stage-2 Full",
    "OCaml baseline",
    "Original system",
]
WORKLOADS = ["SBPF-program", "SBPF-instruction", "x64-stepper"]
RAW_IMPLEMENTATION = {
    ("SBPF-program", "Original system"): "Case-study baseline",
    ("SBPF-instruction", "Original system"): "Case-study baseline",
    ("x64-stepper", "Original system"): "Native x64 baseline",
}
RAW_FILES = {
    "SBPF-program": HERE / "rq3-sbpf-raw.csv",
    "SBPF-instruction": HERE / "rq3-sbpf-raw.csv",
    "x64-stepper": HERE / "rq3-x64-raw.csv",
}
EXPECTED_RAW_SHA256 = {
    "rq3-sbpf-raw.csv": "bd1b3b4b85b6b4140157a46ae656eb24302c182f8c2bf4f7769c124cd0dd6e66",
    "rq3-x64-raw.csv": "5a228939792e927f83ee35eb1425a49541d17cc7e6e707971b5fd6565048e179",
}
EXPECTED_SOLANA_REPETITIONS = {
    "SBPF-program": 20,
    "SBPF-instruction": 1,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def crate_tree_hash(manifest: Path) -> tuple[str, int]:
    root = manifest.parent
    files = [manifest]
    lock = root / "Cargo.lock"
    if lock.is_file():
        files.append(lock)
    files.extend(
        path
        for path in root.rglob("*.rs")
        if "target" not in path.relative_to(root).parts
    )
    digest = hashlib.sha256()
    unique_files = sorted(
        set(files), key=lambda path: path.relative_to(root).as_posix()
    )
    for path in unique_files:
        relative = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), len(unique_files)


def median(values: list[Decimal]) -> Decimal:
    assert len(values) == 3
    return sorted(values)[1]


def rounded_equal(actual: Decimal, displayed: str) -> bool:
    printed = Decimal(displayed.replace(",", ""))
    decimals = len(displayed.partition(".")[2])
    quantum = Decimal(1).scaleb(-decimals)
    return abs(actual - printed) <= quantum / 2


raw_by_file = {path: read_csv(path) for path in set(RAW_FILES.values())}
for name, expected_hash in EXPECTED_RAW_SHA256.items():
    actual_hash = sha256(HERE / name)
    assert actual_hash == expected_hash, (name, actual_hash, expected_hash)

for path, rows in raw_by_file.items():
    assert rows, path
    for row in rows:
        assert row["exit_status"] == "0", row
        assert row["cpu"] == "0", row
        assert int(row["suite_repetitions"]) > 0, row
        assert int(row["logical_units"]) > 0, row
        if row["metric"] == "runtime":
            calculated = Decimal(row["elapsed_seconds"]) / Decimal(
                row["suite_repetitions"]
            )
            assert abs(calculated - Decimal(row["normalized_seconds"])) <= Decimal(
                "0.0000000005"
            ), row


def selected_raw(
    workload: str, implementation: str, metric: str
) -> list[dict[str, str]]:
    raw_implementation = RAW_IMPLEMENTATION.get(
        (workload, implementation), implementation
    )
    rows = [
        row
        for row in raw_by_file[RAW_FILES[workload]]
        if row["benchmark"] == workload
        and row["implementation"] == raw_implementation
        and row["metric"] == metric
    ]
    rows.sort(key=lambda row: int(row["run_id"]))
    assert [int(row["run_id"]) for row in rows] == [1, 2, 3], (
        workload,
        implementation,
        metric,
    )
    assert len({row["input_sha256"] for row in rows}) == 1
    assert len({row["binary_sha256"] for row in rows}) == 1
    if implementation == "Original system" and workload in EXPECTED_SOLANA_REPETITIONS:
        assert {
            int(row["suite_repetitions"]) for row in rows
        } == {EXPECTED_SOLANA_REPETITIONS[workload]}
    return rows


def raw_values(
    workload: str, implementation: str, metric: str, unit: str
) -> list[Decimal]:
    rows = selected_raw(workload, implementation, metric)
    if metric == "runtime":
        return [Decimal(row["normalized_seconds"]) for row in rows]
    divisor = Decimal(1024**2 if unit == "MiB/case" else 1024)
    return [
        Decimal(row["allocated_bytes"]) / Decimal(row["logical_units"]) / divisor
        for row in rows
    ]


runs = read_csv(HERE / "rq3-performance-runs.csv")
assert len(runs) == len(WORKLOADS) * len(IMPLEMENTATIONS) * 2
run_index: dict[tuple[str, str, str], dict[str, str]] = {}
for row in runs:
    key = (row["workload"], row["implementation"], row["metric"])
    assert key not in run_index, key
    run_index[key] = row
    raw_metric = "runtime" if row["metric"] == "Median runtime" else "allocation"
    values = raw_values(
        row["workload"], row["implementation"], raw_metric, row["unit"]
    )
    displayed_runs = [Decimal(row[f"run_{index}"]) for index in range(1, 4)]
    for actual, displayed in zip(values, displayed_runs):
        assert abs(actual - displayed) <= Decimal("0.0000000005"), (
            key,
            actual,
            displayed,
        )
    assert abs(median(values) - Decimal(row["median"])) <= Decimal(
        "0.0000000005"
    ), key

expected_keys = {
    (workload, implementation, metric)
    for workload in WORKLOADS
    for implementation in IMPLEMENTATIONS
    for metric in ("Median runtime", "Heap allocation")
}
assert set(run_index) == expected_keys

table = read_csv(HERE / "rq3-performance.csv")
assert len(table) == len(WORKLOADS) * 4
table_header = list(table[0])
assert table_header[3:] == IMPLEMENTATIONS

for row in table:
    workload = row["workload"]
    metric = row["metric"]
    if metric in ("Median runtime", "Normalized runtime"):
        base_metric = "Median runtime"
    else:
        base_metric = "Heap allocation"
    full = Decimal(run_index[(workload, "Stage-2 Full", base_metric)]["median"])
    for implementation in IMPLEMENTATIONS:
        value = Decimal(run_index[(workload, implementation, base_metric)]["median"])
        actual = value / full if metric.startswith("Normalized") else value
        assert rounded_equal(actual, row[implementation]), (
            workload,
            metric,
            implementation,
            actual,
            row[implementation],
        )

ablations = read_csv(HERE / "rq3-stage2-ablation.csv")
assert len(ablations) == len(WORKLOADS) * 3
expected_ablation_keys = {
    (workload, group)
    for workload in WORKLOADS
    for group in ("Borrow", "Last-Use", "Closure")
}
assert {(row["benchmark"], row["ablated_group"]) for row in ablations} == (
    expected_ablation_keys
)
for row in ablations:
    full = selected_raw(row["benchmark"], "Stage-2 Full", "runtime")
    minus = selected_raw(row["benchmark"], row["implementation"], "runtime")
    ratios = [
        Decimal(minus_row["normalized_seconds"])
        / Decimal(full_row["normalized_seconds"])
        for minus_row, full_row in zip(minus, full)
    ]
    for index, actual in enumerate(ratios, start=1):
        recorded = Decimal(row[f"run_{index}_minus_over_full"])
        assert abs(actual - recorded) <= Decimal("0.0000000005"), row
    ratio_median = median(ratios)
    assert abs(ratio_median - Decimal(row["median_minus_over_full"])) <= Decimal(
        "0.0000000005"
    ), row
    minus_cost = (ratio_median - 1) * 100
    full_speedup = (1 - 1 / ratio_median) * 100
    assert abs(minus_cost - Decimal(row["minus_cost_percent"])) <= Decimal(
        "0.0000005"
    ), row
    assert abs(full_speedup - Decimal(row["full_speedup_percent"])) <= Decimal(
        "0.0000005"
    ), row
    wins = sum(ratio > 1 for ratio in ratios)
    assert int(row["full_wins"]) == wins, row
    expected_conclusion = (
        "Full faster"
        if ratio_median > 1
        else f'{row["implementation"]} faster'
    )
    assert row["conclusion"] == expected_conclusion, row

correctness = read_csv(HERE / "rq3-correctness.csv")
assert len(correctness) == len(WORKLOADS) * len(IMPLEMENTATIONS)
assert {
    (row["workload"], row["implementation"]) for row in correctness
} == {
    (workload, implementation)
    for workload in WORKLOADS
    for implementation in IMPLEMENTATIONS
}
for row in correctness:
    assert row["failed"] == "0", row
    expected = "146" if row["workload"] == "SBPF-program" else "6000"
    assert row["passed"] == expected, row
    source = REPO / row["source_stdout"]
    if source.is_file():
        assert sha256(source) == row["source_sha256"], source

provenance = read_csv(HERE / "rq3-provenance.csv")
for row in provenance:
    if row["frozen_file"]:
        assert sha256(HERE / row["frozen_file"]) == row["frozen_sha256"], row
    origin = REPO / row["origin_path"]
    if origin.is_file():
        assert sha256(origin) == row["origin_sha256"], origin
        if row["frozen_file"] and origin.suffix == ".csv":
            assert read_csv(origin) == read_csv(HERE / row["frozen_file"]), origin

clippy_corpus = read_csv(HERE / "rq3-clippy-corpus.csv")
clippy_diagnostics = read_csv(HERE / "rq3-clippy-diagnostics.csv")
clippy_summary = read_csv(HERE / "rq3-clippy-summary.csv")
assert len(clippy_corpus) == 92
assert Counter(row["suite"] for row in clippy_corpus) == {
    "HOL": 1,
    "Unit": 55,
    "FPP": 36,
}
assert all(row["clippy_exit_status"] == "0" for row in clippy_corpus)
assert len(clippy_diagnostics) == 16
expected_clippy = {
    "clippy::overly_complex_bool_expr": 1,
    "clippy::too_many_arguments": 2,
    "clippy::type_complexity": 4,
    "unconditional_recursion": 9,
}
assert Counter(row["lint"] for row in clippy_diagnostics) == expected_clippy
diagnostics_by_manifest = Counter(row["manifest"] for row in clippy_diagnostics)
for row in clippy_corpus:
    assert int(row["diagnostic_count"]) == diagnostics_by_manifest[row["manifest"]]
    manifest = REPO / row["manifest"]
    if manifest.is_file():
        tree_hash, file_count = crate_tree_hash(manifest)
        assert tree_hash == row["crate_tree_sha256"], manifest
        assert file_count == int(row["hashed_files"]), manifest

summary_index = {(row["kind"], row["name"]): int(row["count"]) for row in clippy_summary}
assert summary_index[("corpus", "Stage-2 crates")] == 92
assert summary_index[("run", "failed crates")] == 0
assert summary_index[("diagnostic", "Total")] == 16
for lint, count in expected_clippy.items():
    assert summary_index[("diagnostic", lint)] == count

historical_solana_raw = (
    REPO / "evaluation/performance/results/20260720-213206+0800/raw.csv"
)
frozen_baseline_raw = (
    REPO / "evaluation/performance/results/20260801-063556+0800/raw.csv"
)
final_stage2_raw = (
    REPO / "evaluation/performance/results/20260806-173656+0800/raw.csv"
)
if (
    historical_solana_raw.is_file()
    and frozen_baseline_raw.is_file()
    and final_stage2_raw.is_file()
):
    frozen_rows = raw_by_file[RAW_FILES["SBPF-program"]]
    historical_rows = read_csv(historical_solana_raw)
    baseline_rows = read_csv(frozen_baseline_raw)
    final_rows = read_csv(final_stage2_raw)
    is_solana = lambda row: row["implementation"] == "Case-study baseline"
    is_stage2 = lambda row: row["implementation"].startswith("Stage-2")
    assert [row for row in frozen_rows if is_solana(row)] == [
        row for row in historical_rows if is_solana(row)
    ]
    assert [row for row in frozen_rows if is_stage2(row)] == [
        row for row in final_rows if is_stage2(row)
    ]
    assert [
        row for row in frozen_rows if not is_solana(row) and not is_stage2(row)
    ] == [
        row for row in baseline_rows if not is_solana(row) and not is_stage2(row)
    ]

solana_stability = {}
for workload in ("SBPF-program", "SBPF-instruction"):
    values = [
        float(value)
        for value in raw_values(workload, "Original system", "runtime", "s")
    ]
    relative_sample_stddev = statistics.stdev(values) / statistics.mean(values)
    solana_stability[workload] = relative_sample_stddev

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--check-paper",
    action="store_true",
    help="also require TOSEM/latex/63rq3.tex to contain the frozen table",
)
args = parser.parse_args()
if args.check_paper:
    assert PAPER.is_file(), PAPER
    paper = " ".join(PAPER.read_text(encoding="utf-8").split())
    table_start = paper.index(r"\label{tab:rq3-performance}")
    table_end = paper.index(r"\end{table*}", table_start)
    paper_table = paper[table_start:table_end]
    for row in table:
        cells = []
        for index, implementation in enumerate(IMPLEMENTATIONS):
            cell = row[implementation]
            if "." not in cell and len(cell) == 4:
                cell = f"{cell[0]},{cell[1:]}"
            if index == 3:
                cell = rf"\textbf{{{cell}}}"
            cells.append(cell)
        expected = "& " + " & ".join(cells) + r" \\"
        assert expected in paper_table, (row["workload"], row["metric"], expected)

print(
    "RQ3 final snapshot verified: 36 metric summaries, 9 paired ablations, "
    "126 frozen raw process rows, 18 correctness records, 92 Stage-2 Clippy "
    "crates, and 16 residual diagnostics."
)
if args.check_paper:
    print("The 12 performance-table rows are synchronized with 63rq3.tex.")
else:
    print("Paper synchronization was not checked; use --check-paper after updating 63rq3.tex.")
for workload, relative_stddev in solana_stability.items():
    print(f"{workload} Solana runtime RSD: {relative_stddev * 100:.2f}%")
