#!/usr/bin/env python3
"""Measure the phase-only RQ1 translation and optimization times.

Translation time is read from Isabelle's persistent timing for each
``export_code`` command.  It therefore excludes theory/proof checking and
Cargo compilation.  Optimization invokes the already-built release
``cargo-opt`` binary on each generated Stage-1 crate and writes to disposable
work directories; building ``cargo-opt`` and compiling Stage-2 crates are
outside the timed region.

Isabelle itself suppresses command-timing protocol messages when elapsed, CPU,
and GC time are all below 1 ms.  A successfully built corpus theory whose sole
``export_code`` command has no persistent message is therefore recorded as
zero with an explicit ``below_isabelle_1ms_threshold`` status.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[3]
WORK = REPO / "evaluation" / ".work" / "rq1" / "timings"
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
EXPECTED_SUITES = {"HCT-standard": 1, "HCT-binary-nat": 1, "Unit": 53, "FPP": 36}
CORPUS_SESSION_PREFIX = "I2R-RQ1-Timing"
HCT_SESSION = "Rust-HOL-Codegenerator_Test"
OPTIMIZER = REPO / "optimize" / "target" / "release" / "cargo-opt"

# Isabelle stores command timings as compressed YXML in its session database.
# Use Isabelle's own Scala API instead of duplicating that private format.
SCALA_TIMING_EXTRACTOR = r'''{
  val session = sys.env("I2R_TIMING_SESSION")
  val store = isabelle.Store(isabelle.Options.init())
  val database = store.output_log_db(session).expand
  val column = isabelle.SQL.Column.bytes("command_timings")
  isabelle.using(isabelle.SQLite.open_database(database)) { db =>
    val bytes = db.execute_query_statementO[isabelle.Bytes](
      "SELECT command_timings FROM isabelle_session_info",
      _.bytes(column)).getOrElse(isabelle.Bytes.empty)
    isabelle.Properties.uncompress(bytes)
      .filter(props => isabelle.Properties.get(props, "name").contains("export_code"))
      .foreach { props =>
        val file = isabelle.Properties.get(props, "file").getOrElse("")
        val elapsed = isabelle.Properties.get(props, "elapsed").getOrElse("0")
        println(file + "\t" + elapsed)
      }
  }
}'''


def tracked_theories() -> list[tuple[str, Path]]:
    result = subprocess.run(
        ["git", "ls-files", "--", "test/unit", "test/fpp"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )
    selected = [
        ("HCT-standard", REPO / "test/HOL_Codegenerator/Generate.thy"),
        ("HCT-binary-nat", REPO / "test/HOL_Codegenerator/Generate_Binary_Nat.thy"),
    ]
    for relative in result.stdout.splitlines():
        if relative.startswith("test/unit/example/"):
            continue
        theory = REPO / relative
        if (
            theory.is_file()
            and theory.name.endswith("_Test.thy")
            and EXPORT_CODE.search(theory.read_text(encoding="utf-8"))
        ):
            suite = "Unit" if relative.startswith("test/unit/") else "FPP"
            selected.append((suite, theory))

    actual = {
        suite: sum(selected_suite == suite for selected_suite, _ in selected)
        for suite in EXPECTED_SUITES
    }
    if actual != EXPECTED_SUITES:
        raise RuntimeError(f"RQ1 corpus mismatch: expected {EXPECTED_SUITES}, found {actual}")
    return selected


def generated_crate(theory: Path) -> Path:
    root = theory.parent / "stage1" / theory.stem
    manifests = [
        path
        for path in root.rglob("Cargo.toml")
        if "target" not in path.relative_to(root).parts
    ]
    if len(manifests) != 1:
        raise RuntimeError(
            f"expected exactly one Stage-1 crate for {theory.relative_to(REPO)}, "
            f"found {len(manifests)}"
        )
    return manifests[0].parent


def write_timing_root(
    session_root: Path,
    theories: list[tuple[str, Path]],
    session_name: str,
) -> None:
    session_root.mkdir(parents=True, exist_ok=True)
    relative_session_dir = os.path.relpath(REPO, session_root)
    corpus = [
        (Path(relative_session_dir) / theory.relative_to(REPO).with_suffix("")).as_posix()
        for suite, theory in theories
        if suite in {"Unit", "FPP"}
    ]
    directories = sorted(
        {
            (Path(relative_session_dir) / theory.parent.relative_to(REPO)).as_posix()
            for suite, theory in theories
            if suite in {"Unit", "FPP"}
        }
    )
    quoted_directories = "\n".join(f'    "{directory}"' for directory in directories)
    quoted_theories = "\n".join(f'    "{theory}"' for theory in corpus)
    text = f'''session "{session_name}" = Rust +
  options [timeout = 1200]
  sessions
    "HOL-Library"
    "Word_Lib"
  directories
{quoted_directories}
  theories [document = false]
{quoted_theories}
'''
    (session_root / "ROOT").write_text(text, encoding="utf-8")


def clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("RUSTC_BOOTSTRAP", None)
    environment.setdefault("ISABELLE_CARGO", shutil.which("cargo") or "cargo")
    return environment


def run_logged(command: list[str], log: Path, *, environment: dict[str, str] | None = None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as target:
        target.write(f"command: {shlex.join(command)}\n")
        target.flush()
        completed = subprocess.run(
            command,
            cwd=REPO,
            env=environment or clean_environment(),
            text=True,
            stdout=target,
            stderr=subprocess.STDOUT,
        )
    if completed.returncode != 0:
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:])
        raise RuntimeError(f"command failed ({shlex.join(command)}):\n{tail}")


def extract_command_timings(session: str) -> list[tuple[str, float]]:
    environment = clean_environment()
    environment["I2R_TIMING_SESSION"] = session
    completed = subprocess.run(
        ["isabelle", "scala", "-e", SCALA_TIMING_EXTRACTOR],
        cwd=REPO,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "cannot read Isabelle command timings")
    rows = []
    for line in completed.stdout.splitlines():
        file, separator, elapsed = line.rpartition("\t")
        if not separator:
            raise RuntimeError(f"unexpected Isabelle timing row: {line!r}")
        rows.append((file, float(elapsed)))
    return rows


def translation_round(
    round_number: int,
    result_dir: Path,
    session_root: Path,
    session_name: str,
    theories: list[tuple[str, Path]],
) -> list[dict[str, object]]:
    common = [
        "isabelle", "build", "-v",
        "-o", "command_timing_threshold=-1",
        "-o", "threads=1",
        "-d", str(REPO),
        "-d", str(session_root),
    ]
    environment = clean_environment()
    run_logged(
        [*common, "-c", HCT_SESSION],
        result_dir / "logs" / f"translation-round-{round_number}-hct.log",
        environment=environment,
    )
    hct = extract_command_timings(HCT_SESSION)
    run_logged(
        [*common, session_name],
        result_dir / "logs" / f"translation-round-{round_number}-unit-fpp.log",
        environment=environment,
    )
    corpus = extract_command_timings(session_name)

    expected = {
        theory.relative_to(REPO).as_posix(): (suite, theory)
        for suite, theory in theories
    }
    seen: set[str] = set()
    rows = []
    for file, elapsed in [*hct, *corpus]:
        normalized = file.replace("\\", "/")
        matches = [relative for relative in expected if normalized.endswith("/" + relative)]
        if not matches:
            continue
        if len(matches) != 1 or matches[0] in seen:
            raise RuntimeError(f"ambiguous or duplicate translation timing row: {file}")
        relative = matches[0]
        seen.add(relative)
        suite, theory = expected[relative]
        rows.append(
            {
                "phase": "translation",
                "round": round_number,
                "suite": suite,
                "case": theory.stem,
                "seconds": f"{elapsed:.9f}",
                "status": "measured",
            }
        )
    for relative, (suite, theory) in expected.items():
        if relative not in seen:
            rows.append(
                {
                    "phase": "translation",
                    "round": round_number,
                    "suite": suite,
                    "case": theory.stem,
                    "seconds": "0.000000000",
                    "status": "below_isabelle_1ms_threshold",
                }
            )
    actual = {suite: sum(row["suite"] == suite for row in rows) for suite in EXPECTED_SUITES}
    if actual != EXPECTED_SUITES:
        raise RuntimeError(
            f"translation timing corpus mismatch in round {round_number}: "
            f"expected {EXPECTED_SUITES}, found {actual}"
        )
    return rows


def build_optimizer(result_dir: Path) -> None:
    run_logged(
        [
            "cargo", "+stable", "build", "--release", "--locked",
            "--manifest-path", str(REPO / "optimize" / "Cargo.toml"),
            "--bin", "cargo-opt",
        ],
        result_dir / "logs" / "build-optimizer.log",
    )
    if not OPTIMIZER.is_file():
        raise RuntimeError(f"optimizer binary not found after release build: {OPTIMIZER}")


def optimization_round(
    round_number: int,
    result_dir: Path,
    theories: list[tuple[str, Path]],
) -> list[dict[str, object]]:
    output_root = result_dir / "optimizer-output" / f"round-{round_number}"
    rows = []
    for index, (suite, theory) in enumerate(theories, start=1):
        source = generated_crate(theory)
        destination = output_root / f"{index:03d}-{theory.stem}"
        if destination.exists():
            shutil.rmtree(destination)
        command = [str(OPTIMIZER), str(source), "--out-dir", str(destination)]
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=REPO,
            env=clean_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        elapsed = time.perf_counter() - started
        if completed.returncode != 0:
            raise RuntimeError(
                f"optimizer failed for {theory.relative_to(REPO)}:\n"
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        rows.append(
            {
                "phase": "optimization",
                "round": round_number,
                "suite": suite,
                "case": theory.stem,
                "seconds": f"{elapsed:.9f}",
                "status": "measured",
            }
        )
        shutil.rmtree(destination)
    if output_root.exists():
        shutil.rmtree(output_root)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]], rounds: int) -> list[dict[str, object]]:
    phases = {str(row["phase"]) for row in rows}
    summary = []
    for suite in EXPECTED_SUITES:
        result: dict[str, object] = {"suite": suite}
        for phase in ("translation", "optimization"):
            if phase not in phases:
                result[f"{phase}_seconds"] = ""
                continue
            totals = [
                sum(
                    float(row["seconds"])
                    for row in rows
                    if row["phase"] == phase and row["suite"] == suite and row["round"] == run
                )
                for run in range(1, rounds + 1)
            ]
            result[f"{phase}_seconds"] = f"{statistics.median(totals):.2f}"
        summary.append(result)
    total: dict[str, object] = {"suite": "Cumulative total"}
    for phase in ("translation", "optimization"):
        values = [row[f"{phase}_seconds"] for row in summary]
        total[f"{phase}_seconds"] = (
            f"{sum(float(value) for value in values):.2f}" if all(values) else ""
        )
    summary.append(total)
    return summary


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all", "translation", "optimization"), default="all")
    parser.add_argument("--rounds", type=positive_int, default=3)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
    result_dir = (args.output_dir or (WORK / timestamp)).resolve()
    result_dir.mkdir(parents=True, exist_ok=False)

    try:
        theories = tracked_theories()
        session_root = result_dir / "sessions"
        session_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_names = [
            f"{CORPUS_SESSION_PREFIX}_{session_tag}_R{run}"
            for run in range(1, args.rounds + 1)
        ]
        session_roots = [session_root / f"round-{run}" for run in range(1, args.rounds + 1)]
        for root, session_name in zip(session_roots, session_names):
            write_timing_root(root, theories, session_name)
        rows: list[dict[str, object]] = []
        if args.phase in {"all", "translation"}:
            for run in range(1, args.rounds + 1):
                print(f">>> RQ1 translation timing round {run}/{args.rounds}", flush=True)
                rows.extend(
                    translation_round(
                        run,
                        result_dir,
                        session_roots[run - 1],
                        session_names[run - 1],
                        theories,
                    )
                )
                write_csv(
                    result_dir / "raw.csv",
                    rows,
                    ["phase", "round", "suite", "case", "seconds", "status"],
                )
        if args.phase in {"all", "optimization"}:
            build_optimizer(result_dir)
            for run in range(1, args.rounds + 1):
                print(f">>> RQ1 optimization timing round {run}/{args.rounds}", flush=True)
                rows.extend(optimization_round(run, result_dir, theories))
                write_csv(
                    result_dir / "raw.csv",
                    rows,
                    ["phase", "round", "suite", "case", "seconds", "status"],
                )

        summary = summarize(rows, args.rounds)
        write_csv(
            result_dir / "summary.csv",
            summary,
            ["suite", "translation_seconds", "optimization_seconds"],
        )
        environment = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "rounds": args.rounds,
            "phase": args.phase,
            "isabelle_threads": 1,
            "measurement_boundary": {
                "translation": "Isabelle export_code command elapsed time",
                "optimization": "release cargo-opt process elapsed time",
                "excluded": "theory/proof checking, optimizer compilation, and Cargo compilation of generated crates",
                "sub_millisecond_translation": "Isabelle suppresses command timing when elapsed, CPU, and GC are all below 1 ms; such successful cases are recorded as zero and marked in raw.csv",
            },
            "isabelle": subprocess.check_output(["isabelle", "version"], text=True).strip(),
            "rustc": subprocess.check_output(["rustc", "+stable", "--version"], text=True).strip(),
        }
        (result_dir / "environment.json").write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"RQ1 timing results: {result_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
