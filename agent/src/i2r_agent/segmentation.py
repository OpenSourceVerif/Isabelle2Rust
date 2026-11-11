"""Executable source dependencies and versioned, dependency-first translation units.

Specification dependencies remain in the original model; only operational type
occurrences participate in scheduling. Boundary contracts never delete facts.
"""
from copy import deepcopy
from .common import Failure
from .program_model import walk, components
from .task_context import fingerprint

INTRINSICS = {'type:fun', 'type:prop', 'type:itself', 'class:HOL.type'}


def dependencies(entity):
    result = set(entity.get('dependencies', []))
    # Do not walk specifications: class theorems can mention every installed instance.
    operational = [entity.get('source_type', {}),
                   [{'arguments': e.get('arguments', []), 'rhs': e.get('rhs', {})} for e in entity.get('execution_equations', []) or []],
                   entity.get('constructors', []), entity.get('fields', [])]
    for _, node in walk(operational):
        if node.get('kind') == 'type' and 'args' in node:
            result.add('type:' + node['name'])
        result.update('class:' + c for c in node.get('sort', []))
    if entity.get('datatype'): result.add(entity['datatype'])
    result.update(entity.get('supers', []))
    return sorted(result - INTRINSICS)


def graph(model):
    edges = {n: dependencies(e) for n, e in model['entities'].items()}
    seen, todo = set(), list(model['entries'])
    while todo:
        n = todo.pop()
        if n in seen or n in INTRINSICS: continue
        seen.add(n); todo.extend(edges.get(n, []))
    return {'edges': {n: edges.get(n, []) for n in sorted(seen)},
            'unknown': sorted(seen - model['entities'].keys()),
            'intrinsics': sorted(INTRINSICS), 'source_version': fingerprint(model)}


def project_functions(model):
    prefixes = {n.split(':', 1)[1].rsplit('.', 1)[0] + '.' for n in model['entries']}
    return {n for n, e in model['entities'].items() if e.get('kind') == 'constant'
            and any(n.split(':', 1)[-1].startswith(p) for p in prefixes)} | set(model['entries'])


def partition(model, boundaries=()):
    g = graph(model)
    rows = {}; intrinsic_contracts=[]
    for row in boundaries:
        n = row.get('source')
        if n in INTRINSICS:
            intrinsic_contracts.append(deepcopy(row));continue
        if n not in g['edges'] or n in rows:
            raise Failure('invalid_partition', 'Boundary must name a unique reachable source entity', row)
        if n in project_functions(model):
            raise Failure('invalid_partition', 'Mandatory business functions cannot be adaptation boundaries, even with an explicit component owner',
                {'rejected_boundary':row,'mandatory_function':n,
                 'correction':'Remove this source ID from boundaries. Keep it as a function/SCC component member; put representation advice and conditions in semantic_obligations. Recompute component membership against the resulting required dependency catalog.',
                 'source_semantics_unchanged':True})
        if row.get('kind') not in {'native', 'inlined', 'trait'} or not row.get('basis') or not row.get('conditions'):
            raise Failure('invalid_partition', 'Boundary requires native/inlined/trait, source basis and conditions', row)
        rows[n] = deepcopy(row)
    # Boundary nodes are implemented in their consumers, but traversing a
    # boundary must never hide another project function from the schedule.
    active, todo = set(project_functions(model) & g['edges'].keys()), list(model['entries'])
    todo += sorted(active)
    expanded = set()
    while todo:
        n = todo.pop()
        if n in expanded: continue
        expanded.add(n)
        if n in rows: continue
        active.add(n); todo.extend(g['edges'].get(n, []))
    unknown = active - model['entities'].keys()
    if unknown: raise Failure('unknown_dependencies', 'Resolve or explicitly adapt missing source entities', sorted(unknown))
    edges = {n: sorted(set(g['edges'].get(n, [])) & active) for n in active}
    groups = components(edges)
    owner = {n: 'unit-' + fingerprint(sorted(group))[:12] for group in groups for n in group}
    units = {}
    for group in groups:
        uid = owner[group[0]]
        units[uid] = {'id': uid, 'members': sorted(group),
            'dependencies': sorted({owner[d] for n in group for d in edges[n] if owner[d] != uid}),
            'boundary_sources': sorted({d for n in group for d in g['edges'].get(n, []) if d in rows}),
            'exports': sorted(set(group) & set(model['entries']))}
    order, done = [], set()
    while len(done) < len(units):
        ready = sorted(u for u, row in units.items() if u not in done and set(row['dependencies']) <= done)
        if not ready: raise Failure('partition_cycle', 'Condensation graph unexpectedly cyclic')
        for u in ready: done.add(u); order.append(u)
    return {'source_version': g['source_version'], 'boundaries': list(rows.values()), 'intrinsic_contracts':intrinsic_contracts,
            'units': units, 'order': order, 'owner': owner,
            'version': fingerprint({'edges': edges, 'boundaries': rows}),
            'original_graph': g}


def consumers(plan, units):
    result = set(units)
    while True:
        more = {u for u, row in plan['units'].items() if result.intersection(row['dependencies'])}
        if more <= result: return result
        result |= more


def next_unit(plan, completed):
    for u in plan['order']:
        if u not in completed and set(plan['units'][u]['dependencies']) <= set(completed): return u
    return None
