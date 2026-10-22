#!/usr/bin/env python3
"""Validated, durable session receipts for a frozen candidate catalogue.

A receipt, not either legacy summary JSON, is the completion fact. All paths
inside the store are relative and validated. Tool/runtime identities remain
evidence; only the frozen source/context/policy identifies a work unit.
"""
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common

POLICY = "owned-constants-v1"
METHOD = "declaration-catalogue-v1"
SCHEMA = 1


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def inventory(root):
    """Content inventory includes ML and external assets, not just .thy files."""
    return {str(p.relative_to(root)): file_digest(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def expected_theories(info, session):
    parents = set(info.get("session_requirements", {}).get(session, [])) | {session}
    return sorted(t["name"] for t in info["theories"] if t["session"] in parents)


def unit_input(entry, session, info, source):
    """Runtime and diagnostic versions deliberately do not enter this identity."""
    return {"policy": POLICY, "context_policy": "original-theories-and-maximal-ancestry-v1",
            "entry": entry, "session": session, "source": source,
            "requested": sorted({t["name"] for t in info["theories"]}),
            "expected": expected_theories(info, session),
            "theories": info["theories"],
            "requirements": info.get("session_requirements", {}).get(session, [])}


def parse_catalogue(path, unit):
    """Reject wrong schema, partial context coverage and foreign declarations."""
    root = ET.parse(path).getroot()
    required = {"schema": "2", "policy": POLICY, "method": METHOD, "unit": digest(unit)}
    if root.tag != "scan" or root.attrib != required:
        raise ValueError("catalogue root/schema/policy/method/unit mismatch")
    if any(node.tag not in {"requested", "loaded", "context", "theory"} for node in root):
        raise ValueError("unknown catalogue element")

    def names(tag):
        nodes = root.findall(tag)
        values = [node.attrib.get("name") for node in nodes]
        if tag in {"requested", "loaded"} and any(
                node.attrib != {"name": node.attrib.get("name")} or len(node) for node in nodes):
            raise ValueError("invalid " + tag + " row")
        if any(not n for n in values) or len(values) != len(set(values)):
            raise ValueError("missing/duplicate " + tag)
        return set(values)

    if names("requested") != set(unit["requested"]):
        raise ValueError("requested theory set mismatch")
    loaded = names("loaded")
    if not set(unit["expected"]) <= loaded <= set(unit["requested"]):
        raise ValueError("loaded theories do not cover required session context")
    if names("theory") != loaded:
        raise ValueError("theory rows do not cover loaded theories")
    paths = {t["name"]: t["path"] for t in unit["theories"]}
    scope = {}
    abbreviations = {}
    owners = {}
    for theory in root.findall("theory"):
        name = theory.attrib["name"]
        if theory.attrib.get("context") != name or set(theory.attrib) != {"name", "context", "declared"}:
            raise ValueError("declaration context mismatch")
        if int(theory.attrib["declared"]) != len(theory):
            raise ValueError("declaration count mismatch")
        constants, aliases, seen = [], [], set()
        for node in theory:
            c = node.attrib.get("name")
            if (node.tag not in {"constant", "abbreviation"} or not c or len(node)
                    or node.attrib != {"name": c, "owner": name} or c in seen):
                raise ValueError("invalid declaration/owner/duplicate")
            seen.add(c)
            # Independent instance branches can introduce the same internal
            # name with different provenance. Retain both branch observations.
            owners.setdefault(c, set()).add(name)
            (constants if node.tag == "constant" else aliases).append(c)
        scope[paths[name]] = sorted(constants)
        abbreviations[paths[name]] = sorted(aliases)
    contexts = {}
    covered = set()
    for context in root.findall("context"):
        name = context.attrib.get("name")
        cover = [n.attrib.get("theory") for n in context]
        if (set(context.attrib) != {"name"} or name not in loaded or name in contexts
                or any(n.tag != "covers" or set(n.attrib) != {"theory"} or len(n) for n in context)
                or len(cover) != len(set(cover)) or not set(cover) <= loaded or name not in cover):
            raise ValueError("invalid maximal context coverage")
        contexts[name] = sorted(cover)
        covered.update(cover)
    if covered != loaded:
        raise ValueError("maximal contexts omit loaded theories")
    if any(len(origins & set(cover)) > 1
           for origins in owners.values() for cover in contexts.values()):
        raise ValueError("constant has conflicting owners inside one context")
    # A declared maximal context cannot also be a strict ancestor of another.
    if any(a != b and a in cover for b, cover in contexts.items() for a in contexts):
        raise ValueError("nonmaximal context")
    return {"scope": scope, "abbreviations": abbreviations,
            "loaded": sorted(loaded), "contexts": contexts}


class Store:
    def __init__(self, base):
        self.base = Path(base).resolve()
        # Files are immutable within a writer generation. Validate each receipt
        # once on startup; a fresh Store performs the independent final audit.
        self._cache = {}
        self._tools_checked = set()

    def path(self, relative):
        path = (self.base / relative).resolve()
        if not path.is_relative_to(self.base):
            raise ValueError("receipt path escapes run directory")
        return path

    def unit_dir(self, unit):
        # Use a content identity, not an unchecked session name, as a filename.
        return self.base / "units" / digest(unit)

    def pointer(self, unit):
        return self.unit_dir(unit) / "current.json"

    def evidence(self, paths):
        evidence = {}
        for path in paths:
            path = Path(path).resolve()
            name = str(path.relative_to(self.base))
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
            evidence[name] = {"sha256": file_digest(path), "bytes": path.stat().st_size}
        return evidence

    def validate(self, receipt, unit):
        if (receipt.get("schema") != SCHEMA or receipt.get("unit") != unit
                or receipt.get("unit_id") != digest(unit)):
            raise ValueError("receipt identity mismatch")
        if (self.base / "scan-contract.json").is_file() and receipt.get("status") != "blocked_dependency":
            generation = receipt.get("tool_generation")
            if generation not in self._tools_checked:
                directory = self.path("tools/" + str(generation))
                files = common.read_json(directory / "tools.json")
                if not files or digest(files) != generation:
                    raise ValueError("missing/wrong tool generation manifest")
                if any(file_digest(directory / name) != sha for name, sha in files.items()):
                    raise ValueError("retained tool generation changed")
                self._tools_checked.add(generation)
        for name, record in receipt.get("evidence", {}).items():
            path = self.path(name)
            if (not path.is_file() or path.stat().st_size != record["bytes"]
                    or file_digest(path) != record["sha256"]):
                raise ValueError("missing/changed receipt evidence: " + name)
        if receipt.get("status") == "complete":
            build, inspect = receipt.get("build", {}), receipt.get("inspect", {})
            if any(c.get("status") != "passed" or c.get("returncode") != 0
                   for c in (build, inspect)):
                raise ValueError("complete requires successful build and inspection")
            for check in (build, inspect):
                log = Path(common.PROJECT / check["log"]).resolve()
                name = str(log.relative_to(self.base))
                if name not in receipt["evidence"]:
                    raise ValueError("command log is not retained")
            xml = self.path(receipt["xml"])
            if receipt["xml"] not in receipt["evidence"]:
                raise ValueError("catalogue XML is not retained")
            if parse_catalogue(xml, unit) != receipt.get("catalogue"):
                raise ValueError("receipt catalogue differs from XML")
        elif receipt.get("status") not in {
                "unresolved_infrastructure", "interrupted", "blocked_dependency", "failed_source"}:
            raise ValueError("unknown receipt status")
        if receipt.get("status") == "blocked_dependency":
            deps = receipt.get("dependencies", [])
            if (not deps or len(deps) != len(set(deps))
                    or not set(deps) <= set(unit["requirements"])
                    or set(receipt.get("causes", {})) != set(deps)):
                raise ValueError("dependency block has no exact causal scope")
        if receipt.get("status") == "failed_source":
            review = receipt.get("source_review", {})
            if not review.get("mechanism") or not review.get("evidence"):
                raise ValueError("source failure requires explicit mechanism/evidence review")
            if not set(review["evidence"]) <= set(receipt.get("evidence", {})):
                raise ValueError("source review evidence not retained")
        return receipt

    def read(self, unit):
        pointer = common.read_json(self.pointer(unit))
        if pointer is None:
            return None
        key = digest(unit)
        cached = self._cache.get(key)
        if cached and cached[0] == pointer:
            return cached[1]
        path = self.path(pointer["receipt"])
        if file_digest(path) != pointer["sha256"]:
            raise ValueError("receipt pointer checksum mismatch")
        receipt = self.validate(common.read_json(path), unit)
        self._cache[key] = (pointer, receipt)
        return receipt

    def commit(self, attempt, receipt):
        """Crash before pointer: old receipt wins; orphan receipt is recoverable."""
        unit = receipt["unit"]
        current = self.read(unit)
        if current and current["status"] == "complete":
            if digest(current) == digest(receipt):
                return current
            raise ValueError("completed session is frozen; reopening is forbidden")
        self.validate(receipt, unit)
        path = attempt / "receipt.json"
        if path.exists():
            if common.read_json(path) != receipt:
                raise ValueError("immutable attempt receipt already exists")
        else:
            common.write_json(path, receipt)
        common.write_json(self.pointer(unit), {
            "receipt": str(path.relative_to(self.base)), "sha256": file_digest(path)})
        return receipt

    def next_attempt(self, unit):
        root = self.unit_dir(unit)
        root.mkdir(parents=True, exist_ok=True)
        number = 1
        while (root / f"attempt-{number:04d}").exists():
            number += 1
        path = root / f"attempt-{number:04d}"
        path.mkdir()
        return path

    def attempts(self, unit):
        return sorted(self.unit_dir(unit).glob("attempt-*"))

    def recover(self, unit):
        """Adopt durable orphan commits or successful XML without reinspection."""
        current = self.read(unit)
        if current and current["status"] == "complete":
            return current
        for attempt in reversed(self.attempts(unit)):
            receipt = common.read_json(attempt / "receipt.json")
            if receipt is not None:
                # Failure/source/blocked receipts are durable facts too; a
                # lost pointer must not cause identical crash attempts again.
                return self.commit(attempt, receipt)
            run = common.read_json(attempt / "attempt.json")
            built = common.read_json(attempt / "load.log.json", {})
            inspected = common.read_json(attempt / "scan.log.json", {})
            if run and all(c.get("status") == "passed" and c.get("returncode") == 0
                           for c in (built, inspected)):
                receipt = completed_receipt(self, attempt, unit, run, built, inspected)
                return self.commit(attempt, receipt)
        return current


def completed_receipt(store, attempt, unit, run, built, inspected):
    """One object binds candidate facts, required coverage and original evidence."""
    if run.get("unit_id") != digest(unit):
        raise ValueError("attempt input identity does not match session")
    xml = attempt / "catalogue.xml"
    catalogue = parse_catalogue(xml, unit)
    evidence = store.evidence([attempt / n for n in (
        "attempt.json", "theories.txt", "load.log", "load.log.json",
        "scan.log", "scan.log.json", "catalogue.xml")])
    return {"schema": SCHEMA, "unit": unit, "unit_id": digest(unit), "status": "complete",
            "committed": common.timestamp(), "build": built, "inspect": inspected,
            "xml": str(xml.relative_to(store.base)), "catalogue": catalogue,
            "tool_generation": run["tool_generation"], "runtime": run["runtime"],
            "evidence": evidence}


def aggregate(store, data, units, metadata):
    """Read committed facts only; summaries cannot manufacture completed work."""
    exports = {entry: {} for entry in data["order"]}
    result = {"schema_version": 2, "environment": metadata, "entries": {}}
    for entry in data["order"]:
        info = data["entries"][entry]
        receipts = [store.read(units[session]) for session in info["sessions"]]
        loading, inspections, paths, contexts = [], [], set(), {}
        for session, receipt in zip(info["sessions"], receipts):
            if not receipt:
                continue
            status = receipt["status"]
            loading.append(dict(receipt.get("build", {"status": status}), session=session))
            if receipt.get("inspect"):
                inspections.append(dict(receipt["inspect"], session=session))
            if status == "complete":
                for path, names in receipt["catalogue"]["scope"].items():
                    exports[entry][path] = sorted(set(exports[entry].get(path, [])) | set(names))
                    paths.add(path)
                contexts[session] = receipt["catalogue"]["contexts"]
        states = [r["status"] if r else "pending" for r in receipts]
        status = ("passed" if states and all(s == "complete" for s in states) else
                  "blocked" if states and all(s == "blocked_dependency" for s in states) else
                  "pending" if "pending" in states else "failed")
        identities = {s: digest(units[s]) for s in info["sessions"]}
        scan = {"status": status, "policy": POLICY, "method": METHOD, "theories": sorted(paths),
                "loading": loading, "inspections": inspections, "contexts": contexts,
                "unit_states": dict(zip(info["sessions"], states)),
                "unit_ids": identities,
                "semantic_identity": digest({"units": identities, "contexts": contexts}),
                "missing_theories": [t for t in info["theories"] if t["path"] not in paths],
                "theory_loading": {"status": "passed" if loading and all(
                    c.get("status") == "passed" for c in loading) else "failed"}}
        result["entries"][entry] = {"status": status, "scan": scan,
                                   "candidate_count": len(common.candidates(exports[entry])),
                                   "theory_count": len(info["theories"])}
    result["coverage"] = {"entries": len(exports), "distinct_candidates": len({
        c for scope in exports.values() for c in common.candidates(scope)})}
    return result, exports


def publish(store, result, exports):
    """Publish one joint snapshot; legacy views are explicitly nonauthoritative."""
    value = {"schema": SCHEMA, "results": result, "exports": exports}
    sha = digest(value)
    path = store.base / "snapshots" / (sha + ".json")
    if not path.exists():
        common.write_json(path, value)
    common.write_json(store.base / "scan-current.json",
                      {"snapshot": str(path.relative_to(store.base)), "sha256": file_digest(path)})
    # Compatibility views may briefly be different generations. Frozen readers
    # resolve scan-current.json or session receipts, never this independent pair.
    common.write_json(store.base / "exports.json", exports)
    common.write_json(store.base / "results.json", result)
    return sha


def load_snapshot(base):
    store = Store(base)
    pointer = common.read_json(store.base / "scan-current.json")
    if not pointer:
        raise ValueError("frozen run has no committed aggregate snapshot")
    path = store.path(pointer["snapshot"])
    if file_digest(path) != pointer["sha256"]:
        raise ValueError("aggregate snapshot checksum mismatch")
    value = common.read_json(path)
    return value["results"], value["exports"]
