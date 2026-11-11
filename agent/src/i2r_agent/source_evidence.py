"""Exact source evidence supplements; no candidate evaluation or oracle edits."""
from copy import deepcopy
import hashlib
import json


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def applications(term):
    args = []
    while isinstance(term, dict) and term.get("kind") == "apply":
        args.append(term["argument"])
        term = term["function"]
    return term, list(reversed(args))


def constructor_literals(entity, model):
    """Keep maximal closed constructor subtrees, byte-structurally unchanged.

    Constructor identities/arities come only from exported datatype declarations.
    Preserve every type annotation and application node, including argument order.
    Never decode strings, evaluate functions, infer constructors by naming, or use
    Rust mappings. Paths and hashes bind each witness to the original source AST.
    """
    constructors = {c["id"].removeprefix("constant:"): len(c.get("fields", []))
                    for e in model["entities"].values() for c in e.get("constructors", [])}
    def closed(term):
        head, args = applications(term)
        return (isinstance(head, dict) and head.get("kind") == "const"
                and head.get("name") in constructors
                and len(args) == constructors[head["name"]]
                and all(closed(arg) for arg in args))
    out = []
    def visit(term, path):
        if not isinstance(term, dict):
            return
        if closed(term):
            # A standalone nullary name is already visible in readable syntax.
            # Nonempty trees preserve hidden literal fields without duplicating
            # every True/False/Nil leaf as an independent witness.
            if term.get("kind") == "apply":
                out.append({"path": path, "term_sha256": identity(term), "term": deepcopy(term)})
            return
        for key in ("function", "argument", "body"):
            if key in term:
                visit(term[key], path + "/" + key)
    # Execution equations are the selected source semantics. Where unavailable,
    # retain specification terms instead; never duplicate both representations.
    equations = entity.get("execution_equations") or []
    if equations:
        for i, eq in enumerate(equations):
            for j, arg in enumerate(eq.get("arguments", [])):
                visit(arg.get("term"), f"/execution_equations/{i}/arguments/{j}/term")
            visit(eq.get("rhs", {}).get("term"), f"/execution_equations/{i}/rhs/term")
    else:
        for i, spec in enumerate(entity.get("specifications", [])):
            for j, rule in enumerate(spec.get("rules", [])):
                visit(rule.get("proposition", {}).get("term"), f"/specifications/{i}/rules/{j}/proposition/term")
    if not out:
        return None
    return {"policy": "exact-source-closed-constructor-subtrees-v1", "source": entity["id"],
            "entity_sha256": identity(entity), "subtrees": out,
            "notice": "Exact typed source AST subtrees at JSON-pointer paths; constructor arguments retain source order. These are source facts, not evaluated or Rust expected values."}


def type_key(typ):
    if typ.get("kind") in {"free", "schematic"}:
        return (typ["kind"], typ.get("name"), typ.get("index"))
    return None


def ground(typ):
    return isinstance(typ, dict) and typ.get("kind") == "type" and all(ground(t) for t in typ.get("args", []))


def match_type(pattern, actual, bindings):
    """Unify an exported polymorphic signature with one exact occurrence type."""
    if not isinstance(pattern, dict) or not isinstance(actual, dict):
        return False
    key = type_key(pattern)
    if key is not None:
        if key in bindings:
            return bindings[key] == actual
        bindings[key] = actual
        return True
    return (pattern.get("kind") == actual.get("kind") == "type"
            and pattern.get("name") == actual.get("name")
            and len(pattern.get("args", [])) == len(actual.get("args", []))
            and all(match_type(p, a, bindings) for p, a in zip(pattern.get("args", []), actual.get("args", []))))


def substitute(typ, bindings):
    key = type_key(typ)
    if key is not None:
        return bindings.get(key, typ)
    return {**typ, "args": [substitute(t, bindings) for t in typ.get("args", [])]} if typ.get("kind") == "type" else typ


def instance_dependencies(model, selected):
    """Resolve only witnessed typed occurrences and exact instance identities.

    Generic functions propagate their exported execution-type substitution into
    their own instance_resolutions. No cross-product of selected types/classes,
    name heuristic, Rust signature inference or candidate implementation is used.
    Only concrete types already witnessed in the source model can bind variables;
    this finite domain prevents invented unbounded polymorphic instantiations.
    Ambiguous/missing/unsupported resolutions add no facts; review stays uncertain.
    """
    entities = model["entities"]
    index = {}
    concrete = set()
    def types(value):
        if isinstance(value, dict):
            if ground(value):
                concrete.add(identity(value))
            for child in value.values():
                types(child)
        elif isinstance(value, list):
            for child in value:
                types(child)
    for name, entity in entities.items():
        inst = entity.get("instance_identity")
        if isinstance(inst, dict) and inst.get("parameter") and inst.get("type_constructor"):
            index.setdefault(inst["parameter"], []).append((name, entity))
        for row in entity.get("instance_resolutions", []):
            types(row.get("type", {}))
        types(entity.get("execution_type", {}))
    result = set()
    pending = [(name, {}) for name in selected if name in entities]
    seen = set()
    while pending:
        name, bindings = pending.pop()
        token = (name, tuple(sorted((str(k), identity(v)) for k, v in bindings.items())))
        if token in seen:
            continue
        seen.add(token)
        for row in entities[name].get("instance_resolutions", []):
            typ = substitute(row.get("type", {}), bindings)
            if not ground(typ):
                continue
            parameter = row.get("constant")
            matches = []
            for target, instance in index.get(parameter, []):
                parameter_entity = entities.get("constant:" + parameter, {})
                bound = {}
                if not match_type(parameter_entity.get("execution_type") or parameter_entity.get("source_type"), typ, bound):
                    continue
                if not any(t.get("name") == instance["instance_identity"]["type_constructor"] for t in bound.values()):
                    continue
                local = {}
                if match_type(instance.get("execution_type") or instance.get("source_type"), typ, local):
                    matches.append(target)
            if len(matches) == 1:
                result.add(matches[0])
            # Direct concrete implementations also retain their exact identity;
            # usual dependency traversal supplies their equations and transitive
            # facts. Forward generic substitution through exact exported calls.
            target = "constant:" + row.get("implementation", "")
            if target not in entities:
                continue
            local = {}
            signature = entities[target].get("execution_type") or entities[target].get("source_type")
            if match_type(signature, typ, local) and all(ground(t) and identity(t) in concrete for t in local.values()):
                pending.append((target, local))
    return result
