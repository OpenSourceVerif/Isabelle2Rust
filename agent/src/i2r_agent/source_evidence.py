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


def constructor_arities(model):
    return {c['id'].removeprefix('constant:'):len(c.get('fields',[]))
            for e in model['entities'].values() for c in e.get('constructors',[])}


def compact_constructor(term,constructors,types):
    """Losslessly flatten saturated constructor applications; never decode values."""
    type_ids={json.dumps(t,sort_keys=True,ensure_ascii=False):key for key,t in types.items()}
    def encode(node):
        arguments=[]
        while isinstance(node,dict) and node.get('kind')=='apply':
            if set(node)!={'kind','function','argument'}:raise ValueError('Unsupported application fields')
            arguments.append(node['argument']);node=node['function']
        arguments.reverse()
        if (not isinstance(node,dict) or set(node)!={'kind','name','type'} or node['kind']!='const' or
            node['name'] not in constructors or len(arguments)!=constructors[node['name']] or
            not isinstance(node['type'],dict)):
            raise ValueError('Not an exact saturated typed constructor')
        key=json.dumps(node['type'],sort_keys=True,ensure_ascii=False)
        if key not in type_ids:
            ref='t'+str(len(types));type_ids[key]=ref;types[ref]=deepcopy(node['type'])
        return [node['name'],type_ids[key],[encode(arg) for arg in arguments]]
    return encode(term)


def restore_constructor(row,types,constructors,used=None):
    """Recover the original typed application AST and check its source digest."""
    used=set() if used is None else used
    def decode(node):
        if (not isinstance(node,list) or len(node)!=3 or not isinstance(node[0],str) or
            node[0] not in constructors or not isinstance(node[1],str) or node[1] not in types or
            not isinstance(types[node[1]],dict) or not isinstance(node[2],list) or
            len(node[2])!=constructors[node[0]]):raise ValueError('Invalid typed constructor tree')
        used.add(node[1]);term={'kind':'const','name':node[0],'type':deepcopy(types[node[1]])}
        for arg in node[2]:term={'kind':'apply','function':term,'argument':decode(arg)}
        return term
    if row.get('representation')=='typed-constructor-tree-v1' and 'term' not in row:
        term=decode(row['tree'])
    elif 'term' in row and 'tree' not in row and 'representation' not in row:
        term=deepcopy(row['term'])
    else:raise ValueError('Unknown constructor evidence representation')
    if identity(term)!=row['term_sha256']:raise ValueError('Constructor source hash mismatch')
    return term


def verify_constructor_evidence(evidence,entity,model):
    """Bind the reversible display to this entity and every original source path."""
    if evidence['source']!=entity['id'] or evidence['entity_sha256']!=identity(entity):
        raise ValueError('Constructor entity identity mismatch')
    used=set();constructors=constructor_arities(model)
    original_rows=literal_subtrees(entity,constructors)
    if [row['path'] for row in evidence['subtrees']]!=[path for path,_ in original_rows]:
        raise ValueError('Constructor source inventory mismatch')
    for row,(_,original) in zip(evidence['subtrees'],original_rows):
        if restore_constructor(row,evidence.get('types',{}),constructors,used)!=original:
            raise ValueError('Constructor source path mismatch')
    if used!=set(evidence.get('types',{})):raise ValueError('Unbound constructor type dictionary')


def literal_subtrees(entity,constructors):
    """The complete original maximal closed-constructor witness inventory."""
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
                out.append((path,term))
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
    return out


def constructor_literals(entity, model):
    """An exactly reversible display of every original closed constructor witness.

    Declared constructor IDs/arities only; preserve all types and ordered fields.
    Unsupported AST shapes keep their raw tree. No literal decoding, evaluation,
    constructor-name heuristics or Rust mappings. Each row retains source hashes.
    """
    constructors=constructor_arities(model);out=[];types={}
    for path,term in literal_subtrees(entity,constructors):
        row={"path":path,"term_sha256":identity(term)};pending_types=deepcopy(types)
        try:tree=compact_constructor(term,constructors,pending_types)
        except ValueError:row['term']=deepcopy(term)
        else:
            row.update(representation='typed-constructor-tree-v1',tree=tree)
            types.update(pending_types)
        out.append(row)
    if not out:return None
    evidence={"policy":"reversible-source-constructor-trees-v2","source":entity['id'],
              "entity_sha256":identity(entity),"types":types,"subtrees":out,
              "notice":"Each tree is [full constructor ID, type reference, ordered argument trees]. Resolve type references in types; empty arguments mean a nullary constructor. Rebuild the original AST by left-associative application of the typed constructor to every argument in order. All fields are preserved, including character bit argument order; no string/number decoding or Rust expected values. term is an unchanged fallback AST. Original entity/path/subtree hashes bind both forms to source."}
    verify_constructor_evidence(evidence,entity,model)
    return evidence


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
