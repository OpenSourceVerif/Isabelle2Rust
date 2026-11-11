"""Agent-owned semantic/context model built from typed Isabelle facts.

Extraction, retrieval, Rust realizations, design judgments and executed evidence
are separate. No Thingol term is used to construct a source entity or use edge.
"""
from copy import deepcopy
import re

from .common import Failure


def walk(value, path='$'):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from walk(child, path + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, path + f'[{i}]')


def components(edges):
    """Iterative Kosaraju; avoid Python recursion limits on library closures."""
    seen, order = set(), []
    for root in edges:
        if root in seen:
            continue
        stack = [(root, False)]
        while stack:
            n, done = stack.pop()
            if done:
                order.append(n)
            elif n not in seen:
                seen.add(n)
                stack.append((n, True))
                stack.extend((d, False) for d in reversed(edges.get(n, [])) if d in edges and d not in seen)
    reverse = {n: [] for n in edges}
    for n, deps in edges.items():
        for d in deps:
            if d in reverse:
                reverse[d].append(n)
    seen, result = set(), []
    for root in reversed(order):
        if root in seen:
            continue
        group, stack = [], [root]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n); group.append(n); stack.extend(reverse[n])
        result.append(sorted(group))
    return result


def build(exports):
    entities, entries = {}, []
    for export in exports:
        if export.get('schema_version') != 1:
            raise Failure('source_model_schema', 'Unsupported Isabelle source-facts schema')
        entries += export['entries']
        for e in export['entities']:
            if e['id'] in entities and entities[e['id']] != e:
                raise Failure('source_model_conflict', 'Conflicting facts from export contexts', e['id'])
            entities[e['id']] = deepcopy(e)
    if not entities or not entries:
        raise Failure('source_model_missing', 'Expected source entities and exported roots')
    uses = []
    for e in list(entities.values()):
        e['type_dependencies'] = sorted({'type:' + node['name'] for _, node in walk(e)
                                         if node.get('kind') == 'type' and 'args' in node})
        e['class_dependencies'] = sorted({'class:' + c for _, node in walk(e) for c in node.get('sort', [])})
        e['value_occurrences'] = []
        for i, eq in enumerate(e.get('execution_equations') or []):
            for path, node in walk(eq['rhs']['term'], f'execution_equations[{i}].rhs.term'):
                if node.get('kind') == 'const':
                    uses.append({'caller': e['id'], 'callee': 'constant:' + node['name'],
                                 'path': path, 'instantiated_type': node['type'],
                                 'fact': 'constant occurrence; not a dynamic call or ownership proof'})
                elif node.get('kind') in {'free', 'schematic', 'bound'}:
                    e['value_occurrences'].append({'equation': i, 'path': path, 'term': deepcopy(node)})
        for c in e.get('constructors', []):
            entities.setdefault(c['id'], {**deepcopy(c), 'name': c['id'].split(':', 1)[1],
                'kind': 'constructor', 'datatype': e['id'], 'dependencies': [],
                'type_dependencies': [e['id']], 'class_dependencies': []})
    for e in entities.values():
        e['callers'] = []
    for use in uses:
        if use['callee'] in entities:
            entities[use['callee']]['callers'].append(use['caller'])
    for e in entities.values():
        e['callers'] = sorted(set(e['callers']))
    edges = {n: e.get('dependencies', []) for n, e in entities.items()}
    return {'schema_version': 1, 'kind': 'isabelle2rust-program', 'entries': sorted(set(entries)),
            'entities': entities, 'uses': uses, 'recursive_groups': [g for g in components(edges)
                if len(g) > 1 or g[0] in edges[g[0]]],
            'provenance': {'extractor': 'I2R_Source_Model', 'proof_terms_exported': False,
                'execution_equations': 'Code_Preproc / Code.equations_of_cert',
                'source_specifications': 'Spec_Rules / Function_Common',
                'types_and_classes': 'Code.get_type / Axclass',
                'variable_identity': 'Bound indices are de Bruijn offsets in the exact term; free/schematic names retain their Isabelle type and index.',
                'limitations': 'Typed elaborated terms, not surface syntax. Uses are occurrences, not alias/liveness analysis. Unknowns stay explicit.'}}


def bindings(bundle):
    loaded = bundle.get('loaded_adapter') or bundle.get('base_adapter') or {}
    return loaded.get('bindings', {})


def boundary_ids(bundle):
    return {b['source'] for key in ['types', 'operations'] for b in bindings(bundle).get(key, [])}


def reachable(model, roots, stops=()):
    seen, queue = set(), list(roots)
    while queue:
        n = queue.pop()
        if n in seen:
            continue
        seen.add(n)
        e = model['entities'].get(n, {})
        queue.extend(e.get('type_dependencies', []) + e.get('class_dependencies', []))
        if n not in stops:
            queue.extend(e.get('dependencies', []))
            queue.extend(c['id'] for c in e.get('constructors', []))
            queue.extend(e.get('supers', []))
    return seen


def readable(entity, model=None):
    """Readable equations plus exact hidden constructor evidence when scoped."""
    e = deepcopy(entity)
    for spec in e.get('specifications', []):
        for rule in spec['rules']:
            rule['proposition'].pop('term', None)
    for eq in e.get('function_input_equations', []):
        eq.pop('term', None)
    for eq in e.get('execution_equations') or []:
        for part in eq['arguments'] + [eq['rhs']]:
            part.pop('term', None)
        if eq.get('theorem'):
            eq['theorem']['proposition'].pop('term', None)
    if model is not None:
        from .source_evidence import constructor_literals
        literal_evidence = constructor_literals(entity, model)
        if literal_evidence:
            e["source_constructor_literals"] = literal_evidence
    return e


def view(bundle, focus=None, original=False):
    model = bundle.get('original_source_model', bundle['source_model']) if original else bundle['source_model']
    roots = set(focus or model['entries'])
    # Include callers of focused operations: interface/representation reasoning
    # needs the context where values are actually used.
    callers = {c for n in roots for c in model['entities'].get(n, {}).get('callers', [])}
    selected = reachable(model, roots | callers, boundary_ids(bundle))
    rows = [readable(model['entities'][n]) for n in sorted(selected) if n in model['entities']]
    return {'kind': model['kind'], 'schema_version': 1, 'entries': model['entries'],
            'focus': sorted(roots), 'entities': rows,
            'uses': [u for u in model['uses'] if u['caller'] in roots | callers],
            'recursive_groups': [g for g in model['recursive_groups'] if selected.intersection(g)],
            'native_boundaries': sorted(selected & boundary_ids(bundle)),
            'unknown_entities': sorted(selected - model['entities'].keys()),
            'catalog': [{'id': n, 'kind': e['kind']} for n, e in model['entities'].items()],
            'selection': 'Roots, their callers and dependency/type closure; expansion stops at effective native bindings. Boundary definitions remain included. Full typed terms and excluded entities are requestable.',
            'provenance': model['provenance']}


def focused_ids(bundle, branch):
    model = bundle.get('original_source_model', bundle['source_model'])
    ids = set(model['entries'])
    ids.update(branch.get('impact', {}).get('affected_source_entities', []))
    from .repair_state import PROTOCOL_ERRORS
    feedback = branch.get('feedback') or {}
    # Missing mapping IDs and malformed edits are protocol work, not evidence
    # that the semantic bodies of every named class/operator are in doubt.
    if feedback.get('status') not in PROTOCOL_ERRORS:
        text = str(feedback)
        for e in model['entities'].values():
            short = e['name'].rsplit('.', 1)[-1]
            if len(short) > 2 and re.search(r'\b' + re.escape(short) + r'\b', text):
                ids.add(e['id'])
    for d in branch.get('decisions', []):
        if d.get('review_required'):
            ids.update(d.get('affected_symbols') or [])
    return ids


def semantic_changes(bundle):
    """Compare exact facts, ignoring relocated source-position metadata only.

    No theorem equivalence inference. Both full versions and their locations
    remain archived, even when no duplicate semantic body needs presenting.
    """
    def facts(e):
        result = deepcopy(e)
        for spec in result.get('specifications', []):
            spec.pop('file', None)
            spec.pop('line', None)
        return result
    before = bundle.get('original_source_model', bundle['source_model'])['entities']
    after = bundle['source_model']['entities']
    return sorted(n for n in before if n not in after or facts(before[n]) != facts(after[n]))


def rust_surface(files):
    """Conservative lexical interface inventory, explicitly not a Rust parser.

    Whole type/impl/module text changes count as representation risk; this
    deliberately over-invalidates rather than certifying missed macro effects.
    """
    result = {}
    pattern = re.compile(r'\b(?:pub(?:\([^)]*\))?\s+)?(?:async\s+|unsafe\s+|const\s+|extern\s+)*'
                         r'(?:fn|struct|enum|trait|type|impl|mod)\b[^;{]*', re.S)
    for path, text in files.items():
        if path.endswith('.rs'):
            result[path] = [' '.join(m[0].split()) for m in pattern.finditer(text)]
    return result


def impact(bundle, before, after, mapping):
    changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
    interfaces_before, interfaces_after = rust_surface(before), rust_surface(after)
    interface_files = [n for n in changed if interfaces_before.get(n) != interfaces_after.get(n)]
    affected = set()
    for row in mapping:
        if not isinstance(row, dict) or not isinstance(row.get('source'), str):
            continue
        item = row.get('rust_item') or row.get('rust')
        if not isinstance(item, str):
            continue
        item = item.split('::')[-1]
        if item and any(re.search(r'\b' + re.escape(item) + r'\b', before.get(n, '') + after.get(n, '')) for n in changed):
            affected.add(row['source'])
    model = bundle['source_model']
    # File-level provenance is intentionally conservative until exact Rust AST
    # symbol resolution is available; missing mapping must not imply no impact.
    if changed and (not affected or interface_files):
        affected.update(model['entries'])
    callers = {c for n in affected for c in model['entities'].get(n, {}).get('callers', [])}
    return {'changed_files': changed, 'interface_change_candidates': interface_files,
            'affected_source_entities': sorted(affected | callers),
            'representation_review_required': bool(changed),
            'method': 'Conservative file/surface inventory and declared realizations; not Rust name resolution or proof of unchanged representation.'}


def record(branch, attempt, before):
    if 'source_model' not in branch.get('bundle', {}):
        return
    from .task_context import fingerprint
    branch['impact'] = impact(branch['bundle'], before, branch['files'], branch.get('mapping', []))
    version = fingerprint(branch['files'])
    implementation = fingerprint({'files': branch['files'], 'connector': branch.get('connector', {}),
        'source_model': branch['bundle']['source_model'], 'plan': branch.get('plan', {})})
    evidence = branch.setdefault('quality_evidence', {})
    # These are separate claims; testing does not upgrade a model cost judgment.
    for row in evidence.values():
        if row.get('implementation_version') != implementation:
            row['current'] = False
    for key, field in [('compile', 'compilation'), ('generic_interface', 'plan_contract')]:
        if attempt.get(field):
            evidence[key] = {'code_version': version, 'implementation_version': implementation,
                             'current': True, 'result': attempt[field]}
    development = attempt.get('development', {})
    if development.get('status') == 'passed' and development.get('behavior_checked') and branch.get('behavior_validated') == version:
        evidence['behavior'] = {'code_version': version, 'implementation_version': implementation, 'current': True, 'status': 'passed',
                                'scope': 'Existing fixed/regression and differential suites; not a proof'}
    if attempt.get('development', {}).get('status') in {'quality_reviewed','quality_refined'}:
        evidence['structure_cost'] = {'code_version': version, 'implementation_version': implementation, 'current': True,
            'status': 'model_reviewed', 'scope': 'Static source/Rust review, not measured performance or proof'}


def context_record(branch):
    return {'realizations': branch.get('mapping', []), 'decisions': branch.get('decisions', []),
            'change_impact': branch.get('impact', {}), 'validation': branch.get('quality_evidence', {}),
            'notice': 'Realizations/decisions are model declarations. Validation results have separate scopes and exact code versions. No new verification gate is introduced.'}
