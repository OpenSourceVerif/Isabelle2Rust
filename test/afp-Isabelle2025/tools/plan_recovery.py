"""Deterministic failure-only isolation; replayable from the run's SQLite receipts."""
import dependency_plan as dp
import frontend_rejection as rejection
from scan_store import digest


def row(context, declaration, status, **extra):
    return dict(declaration, id=dp.declaration_id(declaration), context=context["id"],
                status=status, **extra)


def singleton_requests(context, declarations, trigger, affected=None):
    """Freeze direct requests, including entries previously hidden by coverage.

    With reliable grouping, the scope is the group's covered declarations, not
    its compressed entrance list. Without it the entire context is affected.
    """
    if affected is not None:
        covered = {d for target in dp.TARGETS for d in affected["coverage"][target]["covered"]}
        declarations = [d for d in declarations if dp.declaration_id(d) in covered]
    scope = {"kind": "group" if affected else "context",
             "id": affected["id"] if affected else context["id"]}
    groups = []
    # The failure inventory can contain thousands of full native exceptions.
    # It is identical for every singleton; serialize/hash it once per scope.
    trigger_id = digest(trigger) if declarations else None
    for d in sorted(declarations, key=dp.declaration_id):
        group = {"context": context["id"], "session": context["session"],
                 "parents": context["parents"], "entries": [d["name"]],
                 "targets": list(dp.TARGETS), "module": dp.MODULE, "options": dp.OPTIONS,
                 "kind": "singleton_fallback", "declaration": dp.declaration_id(d),
                 "affected": scope, "trigger": trigger_id}
        group["id"] = digest({"rules": dp.RULES, "input": context["input"],
                              "entry": context["entry"], **group})
        groups.append(group)
    return sorted(groups, key=lambda g: g["id"])


def recover(context, analyze, process=None):
    """analyze returns a sealed graph or failure, never a speculative exclusion."""
    declarations = sorted(context["declarations"], key=dp.declaration_id)
    failures, rejected, known = [], {}, {}
    successful = {}
    unresolved = False

    def inspect(roots):
        value = analyze(roots)
        if value.get("graph") is not None:
            try:
                processed = process(value) if process else {"plan": dp.make_context_plan(context, value["graph"])}
                if "failure" in processed:
                    value = dict(processed, evidence=value["evidence"])
                else:
                    planned = processed["plan"]
                    for d in planned["classifications"]:
                        if d["status"] in {"excluded", "ineligible"}:
                            known[d["id"]] = dict(d, evidence=value["evidence"])
                    successful[tuple(dp.declaration_id(d) for d in roots)] = planned
                    return value, planned
            except Exception as error:
                if process is not None:
                    raise
                import traceback
                value = {"failure": {"phase": "plan_processing", "error": repr(error),
                                     "message": str(error), "traceback": traceback.format_exc()},
                         "evidence": value["evidence"]}
        failure = dict(value["failure"], evidence=value["evidence"],
                       roots=[dp.declaration_id(d) for d in roots])
        failures.append(failure)
        return value, None

    initial, planned = inspect(declarations)
    if planned is not None:
        return planned
    first_reason = rejection.classify(initial["failure"])
    if first_reason:
        pending = [declarations]
        # The root result already exists. Only split failures; successes stop.
        first = True
        while pending:
            roots = pending.pop()
            value, subplan = (initial, None) if first else inspect(roots)
            first = False
            if subplan is not None:
                continue
            reason = rejection.classify(value["failure"])
            if not reason:
                unresolved = True
            elif len(roots) == 1:
                d = roots[0]
                rejected[dp.declaration_id(d)] = row(context, d, "frontend_rejected",
                    reason=reason, failure=value["failure"], evidence=value["evidence"])
            elif roots:
                mid = len(roots) // 2
                pending.extend([roots[mid:], roots[:mid]])
            else:
                unresolved = True
    else:
        unresolved = True

    remaining = [d for d in declarations if dp.declaration_id(d) not in rejected]
    # A single new joint attempt is allowed only after a real rejection changed
    # the root set. If singletons succeed but their union failed, do not repeat it.
    if not unresolved and rejected:
        if remaining:
            planned = successful.get(tuple(dp.declaration_id(d) for d in remaining)) if "scan_theory" in context else None
            if planned is None:
                _, planned = inspect(remaining)
        else:
            planned = {"context": context, "classifications": [], "groups": [], "sccs": []}
        if planned is not None:
            planned["classifications"] = sorted(planned["classifications"] + list(rejected.values()),
                                                key=lambda d: d["id"])
            planned["analysis_failures"] = failures
            return planned
    fallback = [d for d in remaining if dp.declaration_id(d) not in known]
    classifications = list(rejected.values()) + [known[dp.declaration_id(d)] for d in remaining
                                                 if dp.declaration_id(d) in known]
    classifications += [row(context, d, "singleton_fallback") for d in fallback]
    return {"context": context, "classifications": sorted(classifications, key=lambda d: d["id"]),
            "groups": singleton_requests(context, fallback, failures),
            "analysis_failures": failures, "sccs": [], "disposition": "singleton_fallback"}
