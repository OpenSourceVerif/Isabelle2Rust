#!/usr/bin/env python3
"""Current session receipts, with catalogues derived from retained native XML."""
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import afp_common as common
from state import State

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
    """Require the session's own theories, including conditional declarations.

    ROOT `sessions` dependencies make theories available for imports; unlike
    the parent heap, they need not load every dependency theory. Each owning
    session supplies its own coverage receipt, and aggregation checks the full
    entry union. The expected list remains part of the unit identity: retained
    units keep their original requirement instead of being silently redefined.
    """
    return sorted(t["name"] for t in info["theories"] if t["session"] == session)


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
        self.state = State(self.base)

    def path(self, relative):
        path = (self.base / relative).resolve()
        if not path.is_relative_to(self.base):
            raise ValueError("receipt path escapes run directory")
        return path

    def unit_dir(self, unit):
        # Use a content identity, not an unchecked session name, as a filename.
        return self.base / "units" / digest(unit)

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
                log = Path(common.resolve_path(check["log"])).resolve()
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
        raw = self.state.get("receipt/" + digest(unit))
        if raw is None:
            return None
        # The catalogue lives only in native XML. Required contexts come from
        # the run manifest, rather than another copy embedded in every receipt.
        cached = self._cache.get(digest(unit))
        if cached and cached[0] == raw:
            return cached[1]
        receipt = dict(raw, unit=unit)
        for field in ("build", "inspect"):
            if isinstance(receipt.get(field), str):
                receipt[field] = common.read_record(common.resolve_path(receipt[field]))
        if receipt.get("status") == "complete":
            receipt["catalogue"] = parse_catalogue(self.path(receipt["xml"]), unit)
        self.validate(receipt, unit)
        self._cache[digest(unit)] = (raw, receipt)
        return receipt

    def commit(self, attempt, receipt):
        """Commit the replacement before retiring the preceding attempt."""
        unit = receipt["unit"]
        current = self.read(unit)
        if current and current["status"] == "complete" and current != receipt:
            raise ValueError("completed session cannot be reopened")
        self.validate(receipt, unit)
        raw = {k: v for k, v in receipt.items() if k not in {"unit", "catalogue", "runtime"}}
        raw["directory"] = str(attempt.relative_to(self.base))
        for field in ("build", "inspect"):
            check = raw.get(field)
            if check and check.get("log"):
                path = common.resolve_path(check["log"] + ".json")
                common.write_record(path, check)
                raw[field] = common.relative(path)
        self.state.update({"receipt/" + digest(unit): raw},
                          remove=[str((attempt / "attempt.json").relative_to(self.base))])
        self.prune(unit, attempt)
        return receipt

    def prune(self, unit, keep):
        # Retain the committed result and, during execution, at most one active
        # replacement. Orphaned older attempts are retired on the next recovery.
        for previous in self.attempts(unit):
            if previous != keep:
                self.state.remove_tree(previous)

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
        """Recover an exited native child without repeating its expensive work."""
        current = self.read(unit)
        raw = self.state.get("receipt/" + digest(unit), {})
        committed = self.path(raw["directory"]) if raw.get("directory") else None
        if current and current["status"] == "complete":
            self.prune(unit, committed)
            return current
        for attempt in reversed(self.attempts(unit)):
            if attempt == committed:
                continue
            run = common.read_record(attempt / "attempt.json")
            built = common.read_record(attempt / "load.log.json", {})
            inspected = common.read_record(attempt / "scan.log.json", {})
            if run and all(c.get("status") == "passed" and c.get("returncode") == 0
                           for c in (built, inspected)):
                return self.commit(attempt, completed_receipt(self, attempt, unit, run, built, inspected))
            # An uncommitted incomplete attempt may be retried, but not adopted
            # as successful merely because a partial XML or log exists.
            if any(common.identity_matches(c) for c in (built, inspected)):
                raise ValueError("scan child is still running")
            self.state.remove_tree(attempt)
        return current


def completed_receipt(store, attempt, unit, run, built, inspected):
    """One object binds candidate facts, required coverage and original evidence."""
    if run.get("unit_id") != digest(unit):
        raise ValueError("attempt input identity does not match session")
    xml = attempt / "catalogue.xml"
    catalogue = parse_catalogue(xml, unit)
    evidence = store.evidence([attempt / n for n in (
        "theories.txt", "load.log", "scan.log", "catalogue.xml")])
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
        # Successful per-session receipts must also cover the entry manifest.
        # This detects omitted owning sessions or mismatched units without
        # requiring a child heap to load every available dependency theory.
        missing = [t for t in info["theories"] if t["path"] not in paths]
        status = ("passed" if states and all(s == "complete" for s in states) and not missing else
                  "blocked" if states and all(s == "blocked_dependency" for s in states) else
                  "pending" if "pending" in states else "failed")
        identities = {s: digest(units[s]) for s in info["sessions"]}
        scan = {"status": status, "policy": POLICY, "method": METHOD, "theories": sorted(paths),
                "loading": loading, "inspections": inspections, "contexts": contexts,
                "unit_states": dict(zip(info["sessions"], states)),
                "unit_ids": identities,
                "semantic_identity": digest({"units": identities, "contexts": contexts}),
                "missing_theories": missing,
                "theory_loading": {"status": "passed" if loading and all(
                    c.get("status") == "passed" for c in loading) else "failed"}}
        result["entries"][entry] = {"status": status, "scan": scan,
                                   "candidate_count": len(common.candidates(exports[entry])),
                                   "theory_count": len(info["theories"])}
    result["coverage"] = {"entries": len(exports), "distinct_candidates": len({
        c for scope in exports.values() for c in common.candidates(scope)})}
    return result, exports


def load_snapshot(base):
    """Derive the current catalogue; there are no stored aggregate copies."""
    from scan_frozen import make_units
    store = Store(base)
    run = store.state.get("run")
    if not run:
        raise ValueError("Initialize the run first")
    return aggregate(store, run["manifest"], make_units(run["manifest"], run["sources"]), run["environment"])
