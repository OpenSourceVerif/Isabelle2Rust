#!/usr/bin/env python3
"""Freeze, measure and report RQ3 from validated original-source executables.

Default action is check: no performance samples are collected unless --action
measure is explicit. The final RQ2 matrix must be complete. The selected arbitrary Rust mode is
resolved through the matrix's canonical executable aliases; RQ2 timing samples
are never reused as RQ3 samples. All mutations stay in --output.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import math
import platform
import random
import signal
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from i2r_agent.common import ROOT, Failure, digest, now, read, save
from i2r_agent import kernel_build, kernel_timing, timing_drivers, segmented_config, translation_workflow
from i2r_agent.translation_workflow import version


CASE_BATCH_CAPS = {}
CONTROLLER_HISTORY = None
RUST_MODE = "full"
RUST_ID = "full-arbitrary"
IMPLEMENTATIONS = (RUST_ID, "stage2", "ocaml", "haskell", "go")
REFERENCES = IMPLEMENTATIONS[1:]
OPTIONS = {**kernel_timing.DEFAULTS, "processes": 10, "order_design": "williams",
           "samples_per_process": 10, "short_batch_samples": 40}
BOOTSTRAPS = 10000
SEED = 20261114
NUMERICS = {
    "full-arbitrary": "Unified arbitrary backend: Dashu UBig/IBig; compile-time i2r-arbitrary",
    "stage2": "Original Isabelle2Rust Stage2: Dashu UBig/IBig, arbitrary precision",
    "ocaml": "Isabelle OCaml: Zarith Z.t, arbitrary precision",
    "haskell": "Isabelle Haskell: Integer, arbitrary precision",
    "go": "AFP Go: math/big.Int, arbitrary precision",
}
SCOPE_CAVEATS = [
    "This is prepared-input kernel timing. Parsing, preparation and result encoding/verification are outside the timer; kernel results are retained until after timing.",
    "Haskell NFData forces prepared inputs before timing and complete results inside timing. Result traversal is an observer cost inside the Haskell measurement; the eager targets have no corresponding observer traversal. These cross-language results include that evaluation-strategy difference.",
    "For Queue, an optimized identity may return an already prepared container. Haskell forcing still traverses the result. A large cross-language kernel ratio is therefore not evidence of pure algorithmic improvement or end-to-end application speedup.",
    "Rust-S2 borrowed inputs are retained outside the timer. Intrinsic copies, allocations and ownership-consuming operations remain part of each implementation's kernel call.",
    "All five implementations use arbitrary-precision numeric semantics. Checked u128/i128 results belong to RQ2 and are not a cross-language baseline here.",
]


def require(condition, code, detail):
    if not condition:
        raise Failure(code, str(detail))


class Evidence:
    def __init__(self):
        self.files = {}

    def file(self, path, expected=None):
        path = Path(path).resolve()
        require(path.is_file(), "rq3_evidence_missing", path)
        actual = digest(path)
        require(expected is None or actual == expected, "rq3_evidence_changed", path)
        self.files[str(path)] = actual
        return actual

    def json(self, path, expected=None):
        self.file(path, expected)
        return read(path)

    def hashes(self, mapping):
        for path, expected in mapping.items():
            self.file(path, expected)


def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def materialized_hashes(files, connector=False):
    # Match the frozen public materializers exactly: they add this crate-level
    # attribute, which is not part of the model-selected business source.
    prefixed = {"src/lib.rs", "src/main.rs"} if connector else {"src/lib.rs"}
    return {name: hash_text(("#![forbid(unsafe_code)]\n" if name in prefixed else "") + text)
            for name, text in files.items()}


def numeric_feature(config):
    features = config.get("enabled_features", [])
    require("i2r-arbitrary" in features and "i2r-checked" not in features,
            "rq3_numeric_backend_mismatch", features)


def clean_stage_schema(selected, case):
    require(selected.get("stage_schema") == 2, "rq3_clean_source_first_cohort_required", case)


def integrity_review(matrix, evidence):
    path = matrix / "integrity-review.json"
    if not path.exists():
        return {"status": "not_provided", "publication_hold": None, "record": None}
    review = evidence.json(path)
    require(review.get("publication_hold") is not True, "rq3_matrix_publication_hold", path)
    require(review.get("status") != "pending", "rq3_matrix_review_pending", path)
    return {"status": review.get("status", "unspecified"),
            "publication_hold": review.get("publication_hold"), "record": str(path),
            "record_sha256": evidence.files[str(path.resolve())]}


def checked_reference(case, language, status, evidence, preflight):
    require(status.get("status") == "validated", "rq3_reference_not_validated", (case, language))
    build = evidence.json(status["build"])
    require(build["id"] == language and build["language"] == language,
            "rq3_reference_identity_mismatch", (case, language))
    evidence.hashes(build["original_hashes"])
    evidence.hashes(build["artifact_hashes"])
    builder = Path(__file__).with_name("prepare_rq3_baselines.py")
    if digest(builder) != build["builder_sha256"] and CONTROLLER_HISTORY:
        builder = CONTROLLER_HISTORY / (build["builder_sha256"] + ".py")
    evidence.file(builder, build["builder_sha256"])
    evidence.file(timing_drivers.__file__, build["drivers_sha256"])
    binary_sha = evidence.file(build["binary"])
    require(build["artifact_hashes"].get(build["binary"]) == binary_sha,
            "rq3_unsealed_reference_binary", (case, language))
    validation = evidence.json(status["validation"])
    require(validation["status"] == "validated" and validation["binary_sha256"] == binary_sha,
            "rq3_reference_validation_changed", (case, language))
    expected = {(r["lane"], tuple(r["input"])): r["expected"] for r in preflight["observations"]}
    observed = set()
    for lane in validation["lanes"]:
        require(lane["status"] == "passed", "rq3_reference_lane_failed", (case, language, lane))
        rows = evidence.json(lane["full_outputs"])
        require(rows["lane"] == lane["lane"] and len(rows["rows"]) == lane["compared"],
                "rq3_reference_output_count", (case, language, lane["lane"]))
        for row in rows["rows"]:
            key = (lane["lane"], tuple(row["input"]))
            require(key in expected and row["matched"] and row["expected"] == row["actual"] == expected[key],
                    "rq3_reference_output_changed", (case, language, key))
            observed.add(key)
    require(observed == set(expected), "rq3_reference_coverage_changed", (case, language))
    return {"id": language, "language": language, "kind": "original-reference", "case": case,
            "original_binary": build["binary"], "binary_sha256": binary_sha,
            "source_record": status["build"], "source_record_sha256": evidence.files[str(Path(status["build"]).resolve())],
            "numeric_semantics": NUMERICS[language], "canonical_matrix_cell": None}


def checked_rust(case, matrix, result, inputs, evidence):
    directory = matrix / case
    stored = evidence.json(directory / "result.json")
    require(stored == result and result["status"] == "measured", "rq3_matrix_case_changed", case)
    artifact_directory = directory
    if result.get("derived_from"):
        parent = result["derived_from"]
        original = evidence.json(parent["case_result"], parent["sha256"])
        require(original["selections"] == result["selections"], "rq3_projection_selection_changed", case)
        artifact_directory = Path(parent["case_result"]).parent
    elif result.get("measurement_provenance"):
        provenance = evidence.json(result["measurement_provenance"])
        evidence.file(provenance["prior_matrix_seal"], provenance["prior_matrix_seal_sha256"])
        artifact_directory = Path(provenance["prior_matrix_seal"]).parent
    seal = evidence.json(artifact_directory / "matrix-seal.json", result["matrix_seal_sha256"])
    evidence.file(artifact_directory / "baseline/frozen.json", inputs["frozen_sha256"])
    require(seal["baseline"] == inputs["frozen_sha256"], "rq3_baseline_cohort_mismatch", case)
    selected = result["selections"][RUST_MODE]
    require(selected["status"] == "complete" and selected["mode"] == RUST_MODE, "rq3_full_not_final", case)
    clean_stage_schema(selected, case)
    state = evidence.json(selected["selected_state"], selected["selected_state_sha256"])
    require(version(state) == selected["selected_version"] == seal["states"][RUST_MODE],
            "rq3_full_selected_version_changed", case)
    require(seal["selected_state_files"][RUST_MODE] == selected["selected_state_sha256"],
            "rq3_full_selection_seal_changed", case)
    for name, sha in selected["output_files"].items():
        evidence.file(Path(selected["output"]) / name, sha)
    review = Path(selected["selected_state"]).parent / "scope-review"
    evidence.file(review / "review.json", selected["scope_selection"]["review_sha256"])
    evidence.file(review / "selection.json", selected["scope_selection"]["selection_sha256"])
    aliases = result["executable_aliases"]
    canonical = aliases[RUST_ID]
    require(canonical in {"off-arbitrary", "rust-only-arbitrary", RUST_ID}
            and aliases[canonical] == canonical, "rq3_noncanonical_full_alias", (case, canonical))
    validation = evidence.json(directory / "validation.json")
    require(validation["executable_aliases"] == aliases, "rq3_matrix_alias_changed", case)
    for lane in validation["lanes"][RUST_ID]:
        require(lane["status"] == "passed" and not lane["range_exclusions"],
                "rq3_full_validation_failed", (case, lane))
    pair = validation["same_source_pairs"][RUST_MODE]["arbitrary"]
    require(pair["business"] == materialized_hashes(state["files"])
            and pair["connector"] == materialized_hashes(state["connector"], connector=True),
            "rq3_full_algorithm_mismatch", case)
    path = artifact_directory / "builds" / canonical / "timing/build-v2.json"
    build = evidence.json(path)
    require(build["id"] == canonical and build["case"] == case, "rq3_full_build_identity", path)
    evidence.hashes(build["source_hashes"])
    evidence.hashes(build["artifact_hashes"])
    evidence.file(kernel_build.__file__, build["builder_identity"]["builder"])
    evidence.file(timing_drivers.__file__, build["builder_identity"]["drivers"])
    crate = Path(build["source"])
    numeric_feature(evidence.json(crate / "rust-config.json"))
    for category, prefix in [("business", crate), ("connector", crate / "harness"), ("runtime", crate)]:
        for name, sha in pair[category].items():
            evidence.file(prefix / name, sha)
    binary_sha = evidence.file(build["binary"])
    require(build["artifact_hashes"].get(build["binary"]) == binary_sha,
            "rq3_full_binary_unsealed", case)
    declared = {w["id"]: w for w in inputs["workloads"]}
    require({w["workload"] for w in result["rows"]} <= set(declared), "rq3_matrix_workload_changed", case)
    for workload in result["rows"]:
        measurement = evidence.json(workload["record"])
        w = declared[workload["workload"]]
        identity = measurement["identity"]
        require(measurement["status"] == "passed" and measurement["workload"] == w["input"]
                and identity["expected"] == w["expected"] and identity["binaries"][canonical] == binary_sha
                and measurement["executable_aliases"][RUST_ID] == canonical,
                "rq3_matrix_measurement_provenance_changed", (case, w["id"]))
        if measurement.get("measurement_origin"):
            original = evidence.json(measurement["measurement_origin"])
            require(original["identity"] == identity and original["status"] == "passed"
                    and original["summary"][canonical] == measurement["summary"][RUST_ID]
                    and original["processes"][canonical] == measurement["processes"][RUST_ID],
                    "rq3_matrix_canonical_measurement_changed", (case, w["id"]))
    return {"id": RUST_ID, "language": "rust", "kind": "llm", "case": case,
            "original_binary": build["binary"], "binary_sha256": binary_sha,
            "source_record": str(path), "source_record_sha256": evidence.files[str(path.resolve())],
            "numeric_semantics": NUMERICS[RUST_ID], "canonical_matrix_cell": canonical,
            "selected_state": selected["selected_state"], "selected_state_sha256": selected["selected_state_sha256"],
            "source_optimized": selected["selected_source_optimized"]}


def order_design():
    require(kernel_timing.balanced_rounds(5, 10) == 10, "rq3_incomplete_williams_cycle", 5)
    dummy = [{"id": i} for i in IMPLEMENTATIONS]
    orders = [[b["id"] for b in kernel_timing.process_order(dummy, r, "williams")] for r in range(10)]
    positions = {name: Counter(order.index(name) for order in orders) for name in IMPLEMENTATIONS}
    pairs = Counter((a, b) for order in orders for a, b in zip(order, order[1:]))
    require(all(set(row.values()) == {2} and len(row) == 5 for row in positions.values())
            and len(pairs) == 20 and set(pairs.values()) == {2}, "rq3_unbalanced_williams_design", orders)
    return orders


def prepare(preflight, matrix, output, workload_scope="all"):
    evidence = Evidence()
    top = evidence.json(preflight / "rq3-preflight-manifest.json")
    dataset = evidence.json(top["workload_manifest"], top["workload_manifest_sha256"])
    final = evidence.json(matrix / "matrix.json")
    require(final.get("complete") and final.get("measured") == 10, "rq3_final_matrix_required", matrix)
    review = integrity_review(matrix, evidence)
    final_cases = {r["case"]: r for r in final["results"]}
    require(len(top["cases"]) == 10 and set(final_cases) == set(top["cases"]), "rq3_case_set_changed", matrix)
    dataset_cases = {r["id"]: r for r in dataset["cases"] if r["id"] in top["cases"]}
    protocol = evidence.json(preflight / "protocol-audit.json")
    evidence.hashes(protocol["exporter_sources_sha256"])
    # Every reference is independently hash-checked and its complete output
    # validation consumed below; the live batch protocol also checks every result.
    smoke_path = preflight / "protocol-validation.json"
    smoke = evidence.json(smoke_path) if smoke_path.exists() else {"cases": {}}
    cases = {}
    for case, entry in top["cases"].items():
        inputs = evidence.json(entry["inputs"], entry["inputs_sha256"])
        require(inputs["case"] == case and inputs["primary_workload"] == dataset_cases[case]["primary_workload"],
                "rq3_input_case_changed", case)
        require([{k: v for k, v in w.items() if k != "expected"} for w in inputs["workloads"]]
                == dataset_cases[case]["performance_workloads"], "rq3_declared_workloads_changed", case)
        require(final_cases[case]["primary_workload"] == inputs["primary_workload"],
                "rq3_primary_workload_changed", case)
        original = evidence.json(inputs["reference_record"], inputs["reference_record_sha256"])
        for language in ["stage2", "ocaml"]:
            reference = original["references"][language]
            evidence.file(reference["source"], reference["sha256"])
            evidence.file(reference["binary"], reference["binary_sha256"])
        full = checked_rust(case, matrix, final_cases[case], inputs, evidence)
        builds = [full]
        for language in REFERENCES:
            build = checked_reference(case, language, entry["baselines"][language], evidence, inputs)
            if case in smoke["cases"]:
                checked = smoke["cases"][case][language]
                require(checked["status"] == "passed" and checked["binary_sha256"] == build["binary_sha256"]
                        and checked["workloads"] == len(inputs["workloads"]), "rq3_protocol_validation_changed", (case, language))
            builds.append(build)
        cases[case] = {"primary_workload": inputs["primary_workload"], "workloads": [w for w in inputs["workloads"] if workload_scope == "all" or w["id"] == inputs["primary_workload"]],
                       "builds": builds, "input_record": entry["inputs"],
                       "options": {**OPTIONS, "max_batch": CASE_BATCH_CAPS.get(case, OPTIONS["max_batch"])}}
    require(all(c["workloads"] for c in cases.values()), "rq3_no_workloads", cases.keys())
    schedule = [{"case": case, "workload": w["id"], "primary": w["id"] == c["primary_workload"]}
                for primary in [True, False] for case, c in cases.items() for w in c["workloads"]
                if (w["id"] == c["primary_workload"]) == primary]
    source_files = [Path(__file__), Path(kernel_timing.__file__), Path(segmented_config.__file__),
                    Path(translation_workflow.__file__), Path(sys.modules[version.__module__].__file__)]
    program_hashes = {str(p.resolve()): evidence.file(p) for p in source_files}
    identity = {"schema": 1, "preflight": str(preflight), "matrix": str(matrix), "cases": cases,
                "matrix_integrity_review": review,
                "schedule": schedule, "options": OPTIONS, "implementation_order": list(IMPLEMENTATIONS),
                "williams_orders": order_design(), "input_evidence_sha256": evidence.files,
                "program_sha256": program_hashes, "machine": platform.platform(), "architecture": platform.machine(),
                "python": {"executable": sys.executable, "version": sys.version},
                "bootstrap": {"replicates": BOOTSTRAPS, "seed": SEED, "unit": "whole process round",
                              "interval": "95% percentile paired block bootstrap; fixed benchmark suite"},
                "scope_caveats": SCOPE_CAVEATS, "numeric_semantics": NUMERICS, "preflight_tools": protocol["tools"]}
    saved = output / "experiment-seal.json"
    if saved.exists():
        require(read(saved)["identity"] == identity, "rq3_resume_identity_changed", saved)
    else:
        output.mkdir(parents=True, exist_ok=True)
        for path, sha in program_hashes.items():
            target = output / "controller-sources" / (sha + "-" + Path(path).name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        save(saved, {"created_at": now(), "identity": identity})
    for case, row in cases.items():
        for build in row["builds"]:
            target = output / "executables" / case / build["id"] / "reference"
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(".copy-tmp")
                shutil.copy2(build["original_binary"], temporary)
                require(digest(temporary) == build["binary_sha256"], "rq3_binary_copy_failed", target)
                temporary.replace(target)
            require(digest(target) == build["binary_sha256"], "rq3_frozen_binary_changed", target)
    save(output / "plan.json", {"ready": True, "cases": len(cases), "workloads": len(schedule),
        "implementations": list(IMPLEMENTATIONS), "process_rounds_per_workload": 10,
        "normal_samples_per_process": 10, "short_batch_samples_per_process": 40,
        "formal_samples_collected_by_check": 0, "schedule": schedule,
        "experiment_seal_sha256": digest(saved), "scope_caveats": SCOPE_CAVEATS})
    return identity


def verify_evidence(identity):
    for path, sha in identity["input_evidence_sha256"].items():
        require(Path(path).is_file() and digest(path) == sha, "rq3_input_changed_after_sealing", path)


def measurement_path(output, case, workload):
    return output / "measurements" / case / workload


def validated_measurement(identity, output, item):
    case, workload = item["case"], item["workload"]
    path = measurement_path(output, case, workload) / "measurement-v2.json"
    if not path.exists():
        return None
    progress = output / "progress.json"
    if progress.exists():
        recorded = next((r for r in read(progress)["results"]
                         if r["case"] == case and r["workload"] == workload), None)
        if recorded is not None:
            require(digest(path) == recorded["record_sha256"], "rq3_completed_measurement_changed", path)
    result = read(path)
    row = identity["cases"][case]
    w = next(w for w in row["workloads"] if w["id"] == workload)
    binaries = {b["id"]: b["binary_sha256"] for b in row["builds"]}
    require(result["status"] == "passed" and result["case"] == case
            and result["identity"]["options"] == row["options"]
            and result["identity"]["workload"] == w["input"]
            and result["identity"]["expected"] == w["expected"]
            and result["identity"]["binaries"] == binaries
            and result["identity"]["controller"] == identity["program_sha256"][str(Path(kernel_timing.__file__).resolve())],
            "rq3_measurement_identity_changed", path)
    require(set(result["processes"]) == set(IMPLEMENTATIONS), "rq3_missing_implementation", path)
    for name, processes in result["processes"].items():
        require(len(processes) == 10, "rq3_incomplete_process_cycle", (path, name))
        for process in processes:
            samples = process["raw_samples"]
            warm_batch = statistics.median(process["warmup"]["last_samples"]) * process["batch_size"]
            short = min(process["calibration"][-1]["batch_ns"], warm_batch) < (
                identity["options"]["min_batch_ticks"] * process["clock"]["minimum_positive_ns"])
            require(len(samples) == process["sample_count"] and len(samples) in {10, 40}
                    and process["sample_count"] == (40 if short else 10)
                    and all(s["phase"] == "sample" and s["output_checks"] == process["batch_size"]
                            and s["batch_ns"] > 0 for s in samples), "rq3_invalid_sample_record", (path, name))
        require(kernel_timing.summarize(processes) == result["summary"][name],
                "rq3_summary_changed", (path, name))
    for index, order in enumerate(identity["williams_orders"]):
        observed = sorted(IMPLEMENTATIONS, key=lambda name: result["processes"][name][index]["started_at"])
        require(observed == order, "rq3_observed_order_mismatch", (path, index, observed, order))
    return result


def measure(identity, output):
    finished = []
    verify_evidence(identity)
    for item in identity["schedule"]:
        case, workload = item["case"], item["workload"]
        row = identity["cases"][case]
        values = next(w for w in row["workloads"] if w["id"] == workload)
        path = measurement_path(output, case, workload)
        builds = []
        for b in row["builds"]:
            binary = output / "executables" / case / b["id"] / "reference"
            require(digest(binary) == b["binary_sha256"], "rq3_frozen_binary_changed", binary)
            builds.append({**b, "binary": str(binary), "work": str(path / b["id"])})
        kernel_timing.measure_group(case, builds, values["input"], values["expected"], row["options"], path)
        validated_measurement(identity, output, item)
        for b in builds:
            require(digest(b["binary"]) == b["binary_sha256"], "rq3_binary_changed_during_measurement", b["binary"])
        finished.append({**item, "record": str(path / "measurement-v2.json"),
                         "record_sha256": digest(path / "measurement-v2.json")})
        save(output / "progress.json", {"complete": False, "completed_workloads": len(finished),
            "expected_workloads": len(identity["schedule"]), "results": finished, "updated_at": now()})
    verify_evidence(identity)
    save(output / "progress.json", {"complete": True, "completed_workloads": len(finished),
        "expected_workloads": len(identity["schedule"]), "results": finished, "updated_at": now()})


def percentile(values, fraction):
    sorted_values = sorted(values)
    at = (len(sorted_values) - 1) * fraction
    left = math.floor(at)
    right = math.ceil(at)
    return sorted_values[left] + (sorted_values[right] - sorted_values[left]) * (at - left)


def interval(values):
    return [percentile(values, .025), percentile(values, .975)]


def replicate_seed(case, workload):
    return int(hashlib.sha256(f"{SEED}|{case}|{workload}".encode()).hexdigest()[:16], 16)


def workload_bootstrap(case, workload, medians, replicates=BOOTSTRAPS):
    require(set(medians) == set(IMPLEMENTATIONS) and {len(v) for v in medians.values()} == {10}
            and all(x > 0 for v in medians.values() for x in v), "rq3_invalid_bootstrap_samples", (case, workload))
    rng = random.Random(replicate_seed(case, workload))
    runtimes = {name: [] for name in IMPLEMENTATIONS}
    ratios = {name: [] for name in REFERENCES}
    for _ in range(replicates):
        index = [rng.randrange(10) for _ in range(10)]
        sampled = {name: statistics.median(values[i] for i in index) for name, values in medians.items()}
        for name in IMPLEMENTATIONS:
            runtimes[name].append(sampled[name])
        for name in REFERENCES:
            ratios[name].append(sampled[name] / sampled[RUST_ID])
    return runtimes, ratios


def geomean(values):
    return math.exp(statistics.mean(math.log(x) for x in values))


def aggregate(records, comparison, weighting):
    by_case = {}
    for record in records:
        by_case.setdefault(record["case"], []).append(record)
    def combine(values):
        if weighting == "workload_equal":
            return geomean(values(r) for r in records)
        require(weighting == "case_equal", "rq3_unknown_aggregate_weight", weighting)
        return geomean(geomean(values(r) for r in rows) for rows in by_case.values())
    point = combine(lambda r: r["comparisons"][comparison]["speedup"])
    count = len(records[0]["bootstrap"][comparison])
    samples = [combine(lambda r: r["bootstrap"][comparison][i]) for i in range(count)]
    return {"speedup": point, "ci95": interval(samples), "cases": len(by_case), "workloads": len(records),
            "weighting": weighting, "uncertainty_scope": "process-round sampling for this fixed, predeclared suite; cases are not resampled"}


def write_csv(path, rows, fields):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def report(identity, output):
    timing_rows, ratio_rows, quality_rows, records, missing = [], [], [], [], []
    raw_index = []
    for item in identity["schedule"]:
        result = validated_measurement(identity, output, item)
        if result is None:
            missing.append(item)
            continue
        case, workload = item["case"], item["workload"]
        path = measurement_path(output, case, workload) / "measurement-v2.json"
        raw_index.append({**item, "record": str(path), "record_sha256": digest(path)})
        medians = {name: result["summary"][name]["process_medians_ns"] for name in IMPLEMENTATIONS}
        times, ratios = workload_bootstrap(case, workload, medians)
        comparisons = {}
        for name in IMPLEMENTATIONS:
            summary = result["summary"][name]
            low, high = interval(times[name])
            timing_rows.append({**item, "implementation": name, "median_ns": summary["median_ns"],
                "ci95_low_ns": low, "ci95_high_ns": high, "independent_processes": 10,
                "unstable_processes": summary["unstable_processes"], "numeric_semantics": NUMERICS[name],
                "raw_record": str(path)})
            for index, process in enumerate(result["processes"][name]):
                quality_rows.append({**item, "implementation": name, "round": index + 1,
                    "position": identity["williams_orders"][index].index(name) + 1,
                    "batch_size": process["batch_size"], "samples": process["sample_count"],
                    "warmup_stable": process["warmup"]["stable"],
                    "minimum_batch_ns": min(r["batch_ns"] for r in process["raw_samples"]),
                    "timer_probe_ns": process["clock"]["minimum_positive_ns"],
                    "timer_probe_fraction": process["timer_probe_fraction"],
                    "empty_batch_fraction": process["empty_batch_fraction"],
                    "warnings": "|".join(process["warnings"]), "process_evidence": process["evidence"]})
        for reference in REFERENCES:
            point = statistics.median(medians[reference]) / statistics.median(medians[RUST_ID])
            low, high = interval(ratios[reference])
            conclusion = "gain_ci_above_one" if low > 1 else "regression_ci_below_one" if high < 1 else "interval_contains_one"
            comparisons[reference] = {"speedup": point, "ci95": [low, high], "classification": conclusion}
            ratio_rows.append({**item, "reference": reference, "numerator": reference,
                "denominator": RUST_ID, "speedup": point, "ci95_low": low, "ci95_high": high,
                "classification": conclusion, "raw_record": str(path)})
        records.append({**item, "comparisons": comparisons, "bootstrap": ratios})
    primary = [r for r in records if r["primary"]]
    aggregates = {}
    if len(primary) == 10:
        aggregates["primary_case_equal"] = {r: aggregate(primary, r, "case_equal") for r in REFERENCES}
        without_queue = [row for row in primary if row["case"] != "fpp-deq-list"]
        aggregates["sensitivity_primary_without_queue"] = {r: aggregate(without_queue, r, "case_equal") for r in REFERENCES}
    if len(records) == len(identity["schedule"]):
        aggregates["all_workloads_equal"] = {r: aggregate(records, r, "workload_equal") for r in REFERENCES}
        aggregates["all_workloads_case_equal"] = {r: aggregate(records, r, "case_equal") for r in REFERENCES}
    aggregate_rows = [{"scope": scope, "reference": reference, "speedup": row["speedup"],
                       "ci95_low": row["ci95"][0], "ci95_high": row["ci95"][1],
                       "cases": row["cases"], "workloads": row["workloads"], "weighting": row["weighting"]}
                      for scope, values in aggregates.items() for reference, row in values.items()]
    directory = output / "report"
    directory.mkdir(parents=True, exist_ok=True)
    write_csv(directory / "timings.csv", timing_rows, ["case", "workload", "primary", "implementation", "median_ns",
        "ci95_low_ns", "ci95_high_ns", "independent_processes", "unstable_processes", "numeric_semantics", "raw_record"])
    ratio_fields = ["case", "workload", "primary", "reference", "numerator", "denominator", "speedup", "ci95_low", "ci95_high", "classification", "raw_record"]
    write_csv(directory / "speedups.csv", ratio_rows, ratio_fields)
    write_csv(directory / "primary-speedups.csv", [r for r in ratio_rows if r["primary"]], ratio_fields)
    write_csv(directory / "timing-quality.csv", quality_rows, ["case", "workload", "primary", "implementation", "round", "position",
        "batch_size", "samples", "warmup_stable", "minimum_batch_ns", "timer_probe_ns", "timer_probe_fraction", "empty_batch_fraction", "warnings", "process_evidence"])
    write_csv(directory / "geometric-means.csv", aggregate_rows, ["scope", "reference", "speedup", "ci95_low", "ci95_high", "cases", "workloads", "weighting"])
    summary = {"complete": not missing, "measured_workloads": len(records), "expected_workloads": len(identity["schedule"]),
        "measured_primary_workloads": len(primary), "expected_primary_workloads": 10, "missing": missing,
        "speedup_definition": f"reference runtime / {RUST_ID} runtime; above one favors {RUST_ID}",
        "aggregates": aggregates, "comparisons": [{k: v for k, v in r.items() if k != "bootstrap"} for r in records],
        "statistics": {**identity["bootstrap"],
            "point_estimator": "ratio of medians of ten independent-process medians; no raw-batch pseudo-replication",
            "pairing": "same whole process-round index resampled for all five implementations within each workload",
            "aggregate_bootstrap": "independent round resampling for each workload; fixed cases and workload set, then the declared geometric aggregation",
            "primary_weighting": "one predeclared primary workload per case; ten equal case weights",
            "all_workloads_weighting": "equal workload weights and equal case weights after within-case geometric aggregation",
            "interval_limit": "describes process-round sampling uncertainty conditional on this benchmark suite; not a confidence statement over unseen programs or systematic machine drift"},
        "scope_caveats": SCOPE_CAVEATS, "numeric_semantics": NUMERICS,
        "quality_warnings": dict(Counter(w for row in quality_rows for w in row["warnings"].split("|") if w)),
        "no_posthoc_exclusions": True, "raw_records": raw_index,
        "experiment_seal_sha256": digest(output / "experiment-seal.json"), "report_script_sha256": digest(__file__),
        "generated_at": now()}
    save(directory / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True, help="Directory containing rq3-preflight-manifest.json")
    parser.add_argument("--matrix", type=Path, required=True, help="Completed final RQ2 matrix directory, including canonical builds")
    parser.add_argument("--output", type=Path, required=True, help="New RQ3 run directory; all writes stay here")
    parser.add_argument("--action", choices=["check", "measure", "report"], default="check")
    parser.add_argument("--case-max-batch", action="append", default=[], metavar="CASE=N")
    parser.add_argument("--controller-history", type=Path)
    parser.add_argument("--rust-mode", choices=["rust-only", "full"], default="full")
    parser.add_argument("--workloads", choices=["primary", "all"], default="all")
    parser.add_argument("--max-batch", type=int, default=OPTIONS["max_batch"])
    args = parser.parse_args()
    global RUST_MODE, RUST_ID, IMPLEMENTATIONS, CONTROLLER_HISTORY, CASE_BATCH_CAPS
    CASE_BATCH_CAPS = {case: int(value) for case, value in (x.split("=", 1) for x in args.case_max_batch)}
    require(all(n > 0 for n in CASE_BATCH_CAPS.values()), "rq3_invalid_case_batch_cap", CASE_BATCH_CAPS)
    CONTROLLER_HISTORY = args.controller_history.resolve() if args.controller_history else None
    RUST_MODE = args.rust_mode
    RUST_ID = RUST_MODE + "-arbitrary"
    IMPLEMENTATIONS = (RUST_ID, *REFERENCES)
    NUMERICS[RUST_ID] = NUMERICS.pop("full-arbitrary")
    require(args.max_batch > 0, "rq3_invalid_batch_cap", args.max_batch)
    OPTIONS["max_batch"] = args.max_batch
    preflight, matrix, output = (p.resolve() for p in (args.preflight, args.matrix, args.output))
    require(output != preflight and output != matrix and not output.is_relative_to(preflight)
            and not output.is_relative_to(matrix), "rq3_separate_output_required", output)
    output.mkdir(parents=True, exist_ok=True)
    lockpath = ROOT / "cache/timing-v2.lock"
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    with (output / "controller.lock").open("a+") as controller, lockpath.open("a+") as timing:
        fcntl.flock(controller, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(timing, fcntl.LOCK_EX if args.action == "measure" else fcntl.LOCK_SH)
        try:
            identity = prepare(preflight, matrix, output, args.workloads)
            if args.action == "measure":
                measure(identity, output)
            if args.action in {"measure", "report"}:
                summary = report(identity, output)
                print(f"RQ3 report: {summary['measured_workloads']}/{summary['expected_workloads']} workloads, complete={summary['complete']}", flush=True)
            else:
                print(f"RQ3 ready: {len(identity['cases'])} cases, {len(identity['schedule'])} workloads, {RUST_ID}, five implementations, ten Williams rounds; no measurement performed", flush=True)
        except (Exception, KeyboardInterrupt) as error:
            save(output / "last-error.json", {"action": args.action, "at": now(), "code": getattr(error, "code", type(error).__name__),
                "message": str(error), "evidence": getattr(error, "evidence", None), "resume": "Fix the recorded external failure without changing sealed inputs, then rerun the same command."})
            raise


if __name__ == "__main__":
    # Convert termination into normal stack unwinding so a live Session closes
    # its child process and both locks are released before a resumable exit.
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Received signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    main()
