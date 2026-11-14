"""Performance-only, hash-bound source evidence for local primitive symmetry.

This projects already loaded source declarations; it neither proves new theorems
nor licenses a Rust rewrite. Runtime correspondence and event/overflow domains
still require review. No authority is inferred from Rust trait names.
"""
import hashlib
import json
import re
from pathlib import Path


# Exact known declarations, not a benchmark/candidate allowlist. Unknown laws
# have no entry. In particular associativity/distributivity are not licensed.
LAWS = (
    {'primitive': 'Groups.plus_class.plus', 'class': 'Groups.ab_semigroup_add',
     'theory': 'HOL.Groups', 'axiom': 'add_commute',
     'declaration': 'class ab_semigroup_add = semigroup_add + assumes add_commute: "a + b = b + a"'},
    {'primitive': 'Groups.times_class.times', 'class': 'Groups.ab_semigroup_mult',
     'theory': 'HOL.Groups', 'axiom': 'mult_commute',
     'declaration': 'class ab_semigroup_mult = semigroup_mult + assumes mult_commute: "a * b = b * a"'},
)


def _identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _declaration(bundle, law):
    rows = [row for row in bundle.get('source_catalog', []) if row.get('theory') == law['theory']]
    if len(rows) != 1:
        return None
    row = rows[0]
    try:
        raw = Path(row['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row.get('sha256'):
            return None
        text = raw.decode('utf-8')
    except (OSError, ValueError, KeyError, TypeError):
        return None
    # Require the complete exact registered declaration before its begin.
    name = re.escape(law['class'].rsplit('.', 1)[1])
    matches = list(re.finditer(r'(?m)^class\s+' + name + r'\s*=.*?\nbegin\b', text, re.S))
    if len(matches) != 1:
        return None
    match = matches[0]
    declaration = match.group().rsplit('\nbegin', 1)[0]
    if ' '.join(declaration.split()) != law['declaration']:
        return None
    return {'theory': row['theory'], 'source_sha256': row['sha256'],
            'start_line': text.count('\n', 0, match.start()) + 1,
            'end_line': text.count('\n', 0, match.start() + len(declaration)) + 1,
            'declaration': declaration,
            'authority': 'Exact class assumption in hash-verified, previously loaded source catalog'}


def _class_path(entities, start, target):
    queue = [(start, [start])]; seen = set()
    while queue:
        current, path = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        entity = entities.get(current, {})
        if entity.get('kind') != 'class':
            continue
        if current == target:
            return path
        queue.extend((parent, path + [parent]) for parent in entity.get('supers', [])
                     if isinstance(parent, str))
    return None


def _argument_variable(typ):
    # A binary primitive at one type variable. Concrete instances, compound
    # types, mixed variables and missing typed evidence are not inferred here.
    if typ.get('kind') != 'type' or typ.get('name') != 'fun' or len(typ.get('args', [])) != 2:
        return None
    first, rest = typ['args']
    if rest.get('kind') != 'type' or rest.get('name') != 'fun' or len(rest.get('args', [])) != 2:
        return None
    if first.get('kind') not in {'free', 'schematic'} or rest['args'] != [first, first]:
        return None
    return first


def context(state):
    bundle = state['bundle']; model = bundle['source_model']; entities = model['entities']
    evidence = []
    for law in LAWS:
        declaration = _declaration(bundle, law)
        if declaration is None:
            continue
        for source_id, entity in sorted(entities.items()):
            if entity.get('kind') != 'constant':
                continue
            variables = {v['name']: v.get('sort', []) for v in entity.get('type_variables', [])}
            for index, occurrence in enumerate(entity.get('instance_resolutions', [])):
                if occurrence.get('constant') != law['primitive']:
                    continue
                variable_type = _argument_variable(occurrence.get('type', {}))
                if variable_type is None:
                    continue
                variable = variable_type.get('name')
                for sort in variables.get(variable, []):
                    if sort not in variable_type.get('sort', []):
                        continue
                    path = _class_path(entities, 'class:' + sort, 'class:' + law['class'])
                    if path is None:
                        continue
                    row = {'kind': 'source_primitive_operand_symmetry',
                           'source_id': source_id, 'type_variable': variable,
                           'execution_certificate_sort': sort, 'class_path': path,
                           'authority_domain': 'CURRENT typed executable operation and its code-certificate variable sort; not the raw logical export type or an export-genericity proof',
                           'primitive': 'constant:' + law['primitive'],
                           'declaring_class': 'class:' + law['class'],
                           'assumption_binding': law['axiom'],
                           'typed_occurrence_path': f'instance_resolutions[{index}]',
                           'typed_occurrence': occurrence, 'source_evidence': declaration,
                           'permits': 'Value symmetry of the same binary source primitive under this explicitly typed executable sort',
                           'limits': 'Not a Rust rewrite certificate. Verify runtime correspondence, operand evaluation effects, unchanged business event order/count, association and checked overflow/error domain. No recurrence, traversal, reassociation or skipped-operation permission.'}
                    row['evidence_id'] = 'source-law:' + _identity(row)
                    evidence.append(row)
    return {'policy': 'hash-bound-current-source-primitive-laws-v1',
            'absence': 'Missing declarations, source hash mismatch, missing class path or typed occurrence supplies no law authority; names and author claims are insufficient.',
            'evidence': evidence}
