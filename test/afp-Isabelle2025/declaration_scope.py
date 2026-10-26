#!/usr/bin/env python3
"""Relate repeated internal constant names to their scanned source theories.

A per-entry name is an existential export query. Separate declarations sharing
that name need witnesses from contexts containing their own source theory.
"""
import collections
import xml.etree.ElementTree as ET

import afp_common as common
import full


def contexts(info, scan, run):
    """Read actual parents, using frozen ancestry only for inherited sources.

    A failed Context.begin_thy writes no context XML. Its branch number can be
    reconstructed only when the scanned maximal ancestry covers exactly the
    actual loaded originals, in their recorded order. Otherwise leave it unknown.
    """
    work = common.PROJECT / run["directory"]
    loaded_file = work / "loaded.xml"
    if not loaded_file.is_file():
        return {}
    loaded = [node.text for node in ET.parse(loaded_file).getroot().findall("theory")]
    ancestry = scan.get("contexts", {}).get(run.get("session"), {})
    result = {}
    for path in sorted((work / "contexts").glob("*.xml")):
        node = ET.parse(path).getroot()
        parents = {child.text for child in node.findall("theory")}
        theories = set(parents)
        for parent in parents:
            theories.update(ancestry.get(parent, []))
        result[path.stem] = {
            "theories": theories.intersection(loaded),
            "constants": {child.attrib["name"] for child in node.findall("constant")},
            "evidence": [common.relative(loaded_file), common.relative(path)]}
    covered = {name for names in ancestry.values() for name in names}
    if ancestry and covered == set(loaded) and set(ancestry).issubset(loaded):
        maximal = [name for name in loaded if name in ancestry]
        for index, parent in enumerate(maximal, 1):
            result.setdefault("branch" + str(index), {
                "theories": set(ancestry[parent]), "constants": None,
                "evidence": [common.relative(loaded_file)]})
    return result


def applies(context, theory, name, constants, stage):
    """Keep complete batch scopes; missing XML only witnesses context loading."""
    if not context or theory not in context["theories"] or name not in constants:
        return False
    if context["constants"] is None:
        return stage == "context_loading"
    return set(constants).issubset(context["constants"])


def rows(entry, info, record, scope):
    """Yield one row per source declaration without changing candidate totals."""
    owners = collections.Counter(name for names in scope.values() for name in names)
    stage = record.get("full_export", {})
    names = common.candidates(scope)
    theories = {theory["path"]: theory.get("name") for theory in info.get("theories", [])}
    # Parse context inventories once per entry, only when duplicate names need
    # source disambiguation. Ordinary unique names retain their existing cells.
    runs = ([(run, contexts(info, record["scan"], run)) for run in stage.get("runs", [])]
            if any(count > 1 for count in owners.values()) else [])
    for path, constants in sorted(scope.items()):
        for name in sorted(constants):
            context_evidence = set()
            values = stage.get("candidates", {}).get(name, {})
            if owners[name] > 1:
                selected = []
                theory = theories.get(path)
                for run, inventory in runs:
                    attempts = []
                    for attempt in run.get("attempts", []):
                        context = inventory.get(attempt.get("context"))
                        if applies(context, theory, name, attempt["constants"], attempt.get("stage")):
                            attempts.append(attempt)
                            context_evidence.update(context["evidence"])
                    selected.append({"attempts": attempts})
                # resolve_candidates sees each original complete batch, including
                # other names: a failing group must never become a singleton.
                values = full.resolve_candidates(names, selected)[name] if stage else {}
            row = {"entry": entry, "theory": path, "constant": name,
                   "context_evidence": ";".join(sorted(context_evidence))}
            statuses = {attempt.get("evidence"): attempt.get("status")
                        for run in selected for attempt in run["attempts"]} if owners[name] > 1 else {}
            for target in full.TARGETS:
                value = values.get(target, {})
                row[target] = value.get("status", "pending")
                row[target + "_evidence"] = ";".join(
                    evidence for evidence in value.get("evidence", [])
                    if owners[name] == 1 or statuses.get(evidence) == value.get("status"))
            yield row
