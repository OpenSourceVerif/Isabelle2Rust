"""Versioned structural eligibility and deterministic six-target export plans.

Edges point from users to dependencies. Eligibility uses the entire strict
frontend closure. Coverage uses a separate target projection, stopping at
effective printings exactly where native target preparation hides symbols.
"""
from collections import Counter, deque
import json
import xml.etree.ElementTree as ET

from scan_store import digest

RULES = "afp-structural-v2"
SCHEMA = 2
TARGETS = ("Rust", "SML", "OCaml", "Haskell", "Scala", "Go")
SETUPS = ("Rust.Rust_BigInt_Setup", "Go.Go_Setup")
MODULE = "AFP_Code"
OPTIONS = []
KINDS = {"none", "function", "constructor", "class_parameter", "type",
         "class", "class_relation", "instance"}
EQUATIONS = {"missing", "ordinary", "abstract", "projection", "empty", "structural"}


def constant(name):
    return "CONST " + name


def declaration_id(row):
    return digest({k: row[k] for k in ("source", "owner", "name")})


def parse_analysis(path, context):
    root = ET.parse(path).getroot()
    if (root.tag != "analysis" or root.get("schema") != str(SCHEMA)
            or root.get("context") != context["id"]):
        raise ValueError("Native analysis identity mismatch")
    if root.get("status") != "complete":
        raise ValueError("Unresolved native analysis: " + root.findtext("error", "missing evidence"))
    if any(n.tag not in {"node", "declaration", "target"} for n in root):
        raise ValueError("Unknown native analysis record")
    declaration_nodes = root.findall("declaration")
    if any(set(n.attrib) != {"source", "owner", "name", "abstract_constructor"}
           or len(n) for n in declaration_nodes):
        raise ValueError("Invalid native declaration record")
    rows = [{k: n.get(k) for k in ("source", "owner", "name")} for n in declaration_nodes]
    if sorted(rows, key=declaration_id) != sorted(context["declarations"], key=declaration_id):
        raise ValueError("Analysis does not cover exact context declarations")
    declarations = [dict(n.attrib) for n in root.findall("declaration")]
    nodes = {}
    for n in root.findall("node"):
        key = n.get("id")
        if not key or key in nodes:
            raise ValueError("Missing/duplicate native node")
        value = dict(n.attrib)
        if set(value) - {"id", "kind", "equations", "name", "owner",
                          "abstract_constructor", "structural_owner"}:
            raise ValueError("Unknown native node attribute")
        edges = [e.get("to") for e in n]
        if any(e.tag != "edge" or set(e.attrib) != {"to"} for e in n) or len(edges) != len(set(edges)):
            raise ValueError("Invalid native dependency edges")
        value["deps"] = sorted(edges)
        nodes[key] = value
    printings = {}
    for n in root.findall("target"):
        name = n.get("name")
        if name in printings or name not in TARGETS:
            raise ValueError("Missing/duplicate native target")
        syms = [p.get("symbol") for p in n]
        if any(p.tag != "printing" or set(p.attrib) != {"symbol"} for p in n) or len(syms) != len(set(syms)):
            raise ValueError("Invalid native printings")
        printings[name] = sorted(syms)
    graph = {"nodes": nodes, "printings": printings, "declarations": declarations}
    validate_graph(graph)
    return graph


def validate_graph(graph):
    nodes = graph["nodes"]
    if set(graph["printings"]) != set(TARGETS):
        raise ValueError("Analysis needs all six effective printing configurations")
    for key, n in nodes.items():
        kind, eqns = n.get("kind"), n.get("equations")
        valid_equations = ((kind == "none" and eqns in {"missing", "empty"})
                           or (kind == "function" and eqns in {"ordinary", "abstract",
                                                               "projection", "empty"})
                           or (kind not in {"none", "function"} and eqns == "structural"))
        if (kind not in KINDS or eqns not in EQUATIONS or not set(n["deps"]) <= nodes.keys()
                or not valid_equations):
            raise ValueError("Inconsistent native equation/Thingol evidence: " + key)
        if n.get("name") and key != constant(n["name"]):
            raise ValueError("Native constant identity mismatch")
        if kind in {"none", "function", "constructor", "class_parameter"} and (
                not n.get("name") or not n.get("owner")):
            raise ValueError("Constant provenance missing")
        if kind in {"constructor", "class_parameter"} and not n.get("structural_owner"):
            raise ValueError("Structural ownership missing")
    if any(not set(values) <= nodes.keys() for values in graph["printings"].values()):
        raise ValueError("Printing refers outside native program")
    ids = [declaration_id(d) for d in graph["declarations"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate declaration identity")
    for d in graph["declarations"]:
        abstract = d.get("abstract_constructor")
        n = nodes.get(constant(d["name"]))
        if abstract not in {"true", "false"} or (abstract == "false" and
                (not n or n.get("owner") != d["owner"])):
            raise ValueError("Declaration has incomplete native evidence")


def reach(nodes, roots, hidden=()):
    """Generated nodes and printing implementations are disjoint coverage."""
    hidden = set(hidden)
    seen, printed, pending = set(), set(), list(roots)
    while pending:
        key = pending.pop()
        if key in seen or key in printed:
            continue
        if key in hidden:
            printed.add(key)
        else:
            seen.add(key)
            pending.extend(nodes[key]["deps"])
    return seen, printed


def components(nodes):
    """Iterative SCC condensation; independent of graph insertion order."""
    seen, order = set(), []
    for start in sorted(nodes):
        stack = [(start, False)]
        while stack:
            key, done = stack.pop()
            if done:
                order.append(key)
            elif key not in seen:
                seen.add(key)
                stack.append((key, True))
                stack.extend((d, False) for d in reversed(sorted(nodes[key]["deps"])) if d not in seen)
    reverse = {key: [] for key in nodes}
    for key, n in nodes.items():
        for dep in n["deps"]:
            reverse[dep].append(key)
    seen, result = set(), []
    for start in reversed(order):
        if start in seen:
            continue
        group, stack = [], [start]
        while stack:
            key = stack.pop()
            if key not in seen:
                seen.add(key)
                group.append(key)
                stack.extend(reverse[key])
        result.append(sorted(group))
    return sorted(result)


def blocking_paths(nodes, root, blockers):
    """One reproducible shortest path for every reachable blocking node."""
    parents, queue = {root: None}, deque([root])
    while queue:
        key = queue.popleft()
        for dep in sorted(nodes[key]["deps"]):
            if dep not in parents:
                parents[dep] = key
                queue.append(dep)
    result = []
    for blocker in sorted(set(blockers) & parents.keys()):
        path, key = [], blocker
        while key is not None:
            path.append(key)
            key = parents[key]
        result.append({"rule": "R1-missing-implementation", "node": blocker, "path": path[::-1]})
    return result


def make_context_plan(context, graph):
    validate_graph(graph)
    nodes = graph["nodes"]
    missing = {key for key, n in nodes.items() if n["equations"] == "missing"}
    blockers = {t: missing - set(graph["printings"][t]) for t in TARGETS}
    classifications = []
    for d in sorted(graph["declarations"], key=declaration_id):
        row = {k: d[k] for k in ("source", "owner", "name")}
        row.update(id=declaration_id(d), context=context["id"])
        if d["abstract_constructor"] == "true":
            key = constant(d["name"])
            row.update(status="ineligible", rule="R2-abstract-constructor", targets={})
            if key in nodes:
                row.update(kind=nodes[key]["kind"], equations=nodes[key]["equations"])
        else:
            key = constant(d["name"])
            target_info = {t: blocking_paths(nodes, key, blockers[t]) for t in TARGETS}
            row.update(kind=nodes[key]["kind"], equations=nodes[key]["equations"],
                       status="excluded" if all(target_info.values()) else "retained",
                       rule="R1-missing-implementation" if all(target_info.values()) else "R3-eligible",
                       targets={t: {"blocked": bool(paths), "blockers": paths} for t, paths in target_info.items()})
        classifications.append(row)
    retained = {constant(d["name"]): d for d in classifications if d["status"] == "retained"}
    if len(retained) != sum(d["status"] == "retained" for d in classifications):
        raise ValueError("Same name has multiple owners in one context")
    closures = {c: reach(nodes, [c])[0] for c in retained}
    projections = {c: {t: reach(nodes, [c], graph["printings"][t]) for t in TARGETS} for c in retained}
    coverage = {c: {t: (generated | printed) & retained.keys()
                   for t, (generated, printed) in by_target.items()} for c, by_target in projections.items()}
    counts = {t: Counter(obj for c in retained for obj in coverage[c][t]) for t in TARGETS}
    scc = {key: group[0] for group in components(nodes) for key in group}
    selected = set(retained)
    # Condense recursion first, then remove later names whenever all six
    # target projections still cover every retained declaration.
    for c in sorted(retained, key=lambda key: (scc[key], key), reverse=True):
        if all(counts[t][obj] > 1 for t in TARGETS for obj in coverage[c][t]):
            selected.remove(c)
            for t in TARGETS:
                counts[t].subtract(coverage[c][t])
    if any(counts[t][obj] < 1 for t in TARGETS for obj in retained):
        raise ValueError("Retained declaration lacks plan coverage")
    parent = {c: c for c in selected}
    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    owners = set(context["entry_theories"])
    computations = {c for c, n in nodes.items()
                    if n["kind"] in {"function", "none"} and n.get("owner") in owners}
    shared, structural = {}, {}
    for c in sorted(selected):
        footprint = closures[c] & computations
        for dep in sorted(footprint):
            if dep in shared:
                union(c, shared[dep])
            else:
                shared[dep] = c
        if not footprint:
            n = nodes[c]
            key = (n["kind"], n.get("structural_owner") or c)
            if key in structural:
                union(c, structural[key])
            else:
                structural[key] = c
    partitions = {}
    for c in sorted(selected):
        partitions.setdefault(find(c), []).append(c)
    groups = []
    for roots in partitions.values():
        expected = {}
        for t in TARGETS:
            generated, printed = reach(nodes, roots, graph["printings"][t])
            expected[t] = {
                "generated": sorted(generated),
                "printing": sorted(printed),
                "covered": sorted(retained[c]["id"] for c in (generated | printed) & retained.keys())}
        group = {"context": context["id"], "session": context["session"],
                 "parents": context["parents"], "entries": sorted(nodes[c]["name"] for c in roots),
                 "targets": list(TARGETS), "module": MODULE, "options": OPTIONS,
                 "coverage": expected}
        group["id"] = digest({"rules": RULES, "input": context["input"], "entry": context["entry"], **group})
        groups.append(group)
    return {"context": context, "classifications": classifications,
            "groups": sorted(groups, key=lambda g: g["id"]),
            "sccs": components(nodes)}


def assemble(entry, identity, contexts, unresolved_contexts=()):
    contexts = sorted(contexts, key=lambda p: p["context"]["id"])
    payload = {"schema": SCHEMA, "rules": RULES, "entry": entry, "input": identity,
               "contexts": contexts, "unresolved_contexts": list(unresolved_contexts)}
    return dict(payload, id=digest(payload))


def verify_plan(plan, expected):
    """Recomputed from sealed native bytes, never trusted cached coverage."""
    if plan != expected:
        raise ValueError("Stale or altered fixed dependency plan")
    for ctx in plan["contexts"]:
        retained = {d["id"] for d in ctx["classifications"] if d["status"] == "retained"}
        for t in TARGETS:
            covered = {c for g in ctx["groups"] for c in g.get("coverage", {}).get(t, {}).get("covered", [])}
            if covered != retained:
                raise ValueError("Plan does not cover every retained declaration")
        fallback = [d["id"] for d in ctx["classifications"] if d["status"] == "singleton_fallback"]
        requested = [g["declaration"] for g in ctx["groups"] if g.get("kind") == "singleton_fallback"]
        if sorted(fallback) != sorted(requested):
            raise ValueError("Fallback requests do not cover exact declaration identities")
    original = {declaration_id(d) for d in plan["input"].get("declarations", [])}
    disposed = {d["id"] for ctx in plan["contexts"] for d in ctx["classifications"]}
    disposed.update(declaration_id(d) for u in plan.get("unresolved_contexts", []) for d in u["declarations"])
    if "declarations" in plan["input"] and disposed != original:
        raise ValueError("Plan disposition inventory is incomplete")
    return plan


def statistics(plan):
    rows = [d for ctx in plan["contexts"] for d in ctx["classifications"]]
    groups = [g for ctx in plan["contexts"] for g in ctx["groups"]]
    return {"declarations": len({declaration_id(d) for d in plan["input"].get("declarations", rows)}),
            "context_declarations": len(rows),
            "frontend_rejected": sum(d["status"] == "frontend_rejected" for d in rows),
            "singleton_fallback": sum(d["status"] == "singleton_fallback" for d in rows),
            "unresolved_contexts": len(plan.get("unresolved_contexts", [])),
            "normal_groups": sum(g.get("kind") != "singleton_fallback" for g in groups),
            "retained": sum(d["status"] == "retained" for d in rows),
            "excluded": sum(d["status"] == "excluded" for d in rows),
            "ineligible": sum(d["status"] == "ineligible" for d in rows),
            "entries": sum(len(g["entries"]) for g in groups), "groups": len(groups),
            # A recursive coverage projection may mention one declaration from
            # more than one frozen entrance. Report the covered identity union,
            # so this is a structural coverage count rather than a batch count.
            "structural_coverage": {t: len({d for g in groups for d in g.get("coverage", {}).get(t, {}).get("covered", [])})
                                    for t in TARGETS},
            "printing_implementations": {t: len({d for g in groups
                                                   for d in g.get("coverage", {}).get(t, {}).get("printing", [])})
                                           for t in TARGETS}}
