"""Proof-checked source forks for the optional performance stage.

The controller owns theory headers, export roots, and unconditional equivalence
statements. Original theories and original observation contracts are immutable.
"""
from copy import deepcopy
from pathlib import Path
import re
from .common import Failure, read, save
from .task_context import fingerprint
from .program_model import readable
from .segmentation import graph, partition, project_functions


def check_fragment(text):
    if not isinstance(text, str):
        raise Failure('invalid_source_proposal', 'Source fragments must be text')
    # Commands and proof methods are checked by the trusted Isabelle lexer,
    # which handles nested comments and quoted text correctly.
    return text


def source_guard(proposal):
    """Use Isabelle's own outer lexer before executing any proposed command.

The trusted ML file contains escaped string data, never interpolated ML code or
an outer cartouche that a proposed fragment could close.
"""
    texts = [check_fragment(proposal.get('definitions'))]
    texts += [check_fragment(r.get('proof')) for r in proposal.get('replacements', [])]
    allowed = '''fun function primrec definition abbreviation lemma theorem lemmas
declare termination datatype record type_synonym proof qed by apply done using
unfolding from with then hence thus have show fix assume presume obtain let note
next case supply subgoal also finally moreover ultimately . .. { }'''.split()
    def sml_string(value):
        return '"' + ''.join('\\' + f'{b:03d}' for b in value.encode('utf-8')) + '"'
    return ('local\nval allowed = [' + ','.join(sml_string(s) for s in allowed) + '];\n'
            'val fragments = [' + ','.join(sml_string(s) for s in texts) + '];\n'
            'val forbidden = ["tactic", "raw_tactic", "quick_and_dirty", "skip_proofs"];\n'
            'fun check text = List.app (fn tok => if\n'
            '  (Token.is_command tok andalso not (member (op =) allowed (Token.content_of tok)))\n'
            '  orelse (Token.is_proper tok andalso member (op =) forbidden (Token.content_of tok))\n'
            '  then error ("I2R: forbidden source command " ^ Token.content_of tok) else ())\n'
            '  (Token.explode (Thy_Header.get_keywords @{theory}) Position.none text);\n'
            'in val _ = List.app check fragments end;\n')


def type_scheme(typ):
    """Canonicalize type variables without erasing sharing or sort constraints."""
    variables = {}
    def visit(t):
        if t['kind'] == 'type':
            return ('type', t['name'], tuple(visit(a) for a in t.get('args', [])))
        if t['kind'] not in {'schematic', 'free'}:
            raise Failure('source_type_unsupported', str(t))
        key = (t['kind'], t['name'], t.get('index'))
        variables.setdefault(key, len(variables))
        return ('variable', variables[key], tuple(sorted(set(t.get('sort', [])))))
    return visit(typ)


def preserve_export_types(original, revised, roots):
    evidence = {}
    for old, new in roots.items():
        before = original['entities'][old]['source_type']
        after = revised['entities'][new]['source_type']
        if type_scheme(before) != type_scheme(after):
            raise Failure('source_export_type_changed', 'Proved replacement specializes or changes the original type scheme',
                          {'original': old, 'replacement': new, 'before': before, 'after': after})
        evidence[old] = {'replacement': new, 'type_scheme_sha256': fingerprint(type_scheme(before))}
    return evidence


def checked_export_types(evidence, roots):
    """Check trusted source-context constraints, never inferred execution sorts."""
    if (not isinstance(evidence, dict)
            or evidence.get('authority') != 'Sign.the_const_constraint'
            or not isinstance(evidence.get('original'), dict)
            or not isinstance(evidence.get('revised'), dict)
            or set(evidence['original']) != set(roots)
            or set(evidence.get('revised', {})) != set(roots.values())):
        raise Failure('source_type_evidence_missing', 'Incomplete trusted export type evidence')
    for side in ('original', 'revised'):
        for typ in evidence[side].values():
            def complete(t):
                if not isinstance(t, dict) or not isinstance(t.get('name'), str):
                    return False
                if t.get('kind') == 'type':
                    return isinstance(t.get('args'), list) and all(complete(a) for a in t['args'])
                return (t.get('kind') in {'free', 'schematic'}
                        and isinstance(t.get('sort'), list)
                        and all(isinstance(c, str) for c in t['sort'])
                        and (t['kind'] != 'schematic' or isinstance(t.get('index'), int)))
            if not complete(typ):
                raise Failure('source_type_evidence_missing', 'Incomplete trusted export type scheme')
    return preserve_export_types(
        {'entities': {n: {'source_type': t} for n, t in evidence['original'].items()}},
        {'entities': {n: {'source_type': t} for n, t in evidence['revised'].items()}}, roots)


def verify_export_type_evidence(proof, roots):
    """Verify new proof sidecars on restore; legacy proofs retain their raw gate."""
    if 'export_type_authority' not in proof and 'export_type_evidence_sha256' not in proof:
        return False
    if proof.get('export_type_authority') != 'Sign.the_const_constraint in imported original theory context':
        raise Failure('source_type_evidence_missing', 'Unknown trusted export type authority')
    try:
        evidence = read(Path(proof['directory']) / 'export-types.json')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Failure('source_type_evidence_missing', 'Trusted export type sidecar is missing or invalid') from exc
    if fingerprint(evidence) != proof.get('export_type_evidence_sha256'):
        raise Failure('source_type_evidence_changed', 'Trusted export type sidecar hash changed')
    types = checked_export_types(evidence, roots)
    if types != proof.get('export_type_preservation'):
        raise Failure('source_type_evidence_changed', 'Trusted export type preservation evidence changed')
    return True


def render(bundle, proposal, type_evidence_path=None):
    """Generate fixed theorem goals: optimized_i = original_export_i."""
    definitions = check_fragment(proposal.get('definitions'))
    entries = bundle['original_source_model']['entries']
    replacements = proposal.get('replacements', [])
    if (not isinstance(replacements, list) or any(not isinstance(r, dict) or not isinstance(r.get('source'), str) for r in replacements)
            or len(replacements) != len(entries)
            or {r.get('source') for r in replacements} != set(entries)):
        raise Failure('invalid_source_proposal', 'Supply exactly one replacement and proof for every original export', entries)
    original_export = bundle['sources'].get('Export.thy', '')
    match = re.search(r'\bimports\s+(.*?)\s+begin\b', original_export, re.S)
    if not match:
        raise Failure('source_export_layout_unsupported', 'Expected explicit Export theory imports')
    imports = match.group(1)
    # Retain the trusted original imports, including the registered exporter.
    rows = {r['source']: r for r in replacements}
    theory = ('theory Optimization imports ' + imports
              + '\nbegin\ndeclare [[quick_and_dirty = false]]\nML_file "Source_Guard.ML"\n\n' + definitions + '\n\n')
    roots = {}; theorem_names = []
    for i, source in enumerate(entries):
        row = rows[source]; rhs = row.get('rhs'); proof = check_fragment(row.get('proof'))
        if not isinstance(rhs, str) or not rhs.strip() or any(c in rhs for c in ['"', '\n', '\r']):
            raise Failure('invalid_source_proposal', 'rhs must be a single HOL term without a string delimiter')
        name = 'i2r_entry_' + str(i); theorem = 'i2r_equiv_' + str(i)
        theory += ('definition ' + name + ' where "' + name + ' = (' + rhs + ')"\n'
                   'lemma ' + theorem + ': "' + name + ' = ' + source.split(':', 1)[1] + '"\n'
                   + proof + '\n\n')
        roots[source] = 'constant:Optimization.' + name
        theorem_names.append(theorem)
    # Class-local constants have sort-erased kernel declarations, with their
    # source interface restored by Sign.add_const_constraint (class.ML).
    # Read that authoritative interface in the original imported theory context;
    # execution-equation sorts may be stronger and are not a substitute.
    type_audit = ''
    if type_evidence_path is not None:
        def sml_string(value):
            return '"' + ''.join('\\' + f'{b:03d}' for b in str(value).encode('utf-8')) + '"'
        def schemes(names):
            return 'I2R_Source_Model.obj [' + ','.join(
                '(' + sml_string(n) + ', I2R_Source_Model.typ '
                '(Sign.the_const_constraint @{theory} ' + sml_string(n.split(':', 1)[1]) + '))'
                for n in names) + ']'
        type_audit = ('val _ = File.write (Path.explode ' + sml_string(type_evidence_path) + ') '
                      '(I2R_Source_Model.obj [("authority", I2R_Source_Model.quote "Sign.the_const_constraint"),'
                      '("original", ' + schemes(roots) + '),("revised", ' + schemes(roots.values()) + ')]);\n')
    # Inspect the proof dependencies, not merely successful Isabelle exit.
    theory += ('ML \\<open>\n'
               'val {eqngr, ...} = Code_Preproc.obtain true {ctxt = @{context}, consts = ['
               + ', '.join('@{const_name ' + n.split(':', 1)[1] + '}' for n in roots.values())
               + '], terms = []};\n'
               'val equation_proofs = maps (fn c =>\n'
               '  let val (_, equations) = Code.equations_of_cert @{theory} (Code_Preproc.cert eqngr c)\n'
               '  in map_filter (fn (_, (proof, _)) => proof) (these equations) end) (Code_Preproc.all eqngr);\n'
               'val _ = if null (Thm_Deps.all_oracles (@{thms '
               + ' '.join(theorem_names)
               + '} @ equation_proofs)) then () else error "I2R: source equivalence or executable equations use an oracle";\n'
               + type_audit + '\\<close>\nend\n')
    export = ('theory Export imports Optimization "I2R_Agent.Agent_Export" begin\nexport_code '
              + ' '.join(n.split(':', 1)[1] for n in roots.values())
              + ' in Rust_Agent module_name Candidate\nend\n')
    return theory, export, roots


def prove(original, proposal, cfg, executor, directory):
    """Re-enter the existing proof-preserving source extractor on a fork."""
    from .source_input import preprocess
    directory = Path(directory); project = directory / 'project'
    project.mkdir(parents=True, exist_ok=True)
    render(original['bundle'], proposal)  # Validate the envelope before symbol transport or tools.
    from .optimization_source_text import prepare
    proposal, text_encoding = prepare(proposal, cfg, executor, directory)
    type_evidence_path = (directory / 'export-types.json').resolve()
    type_evidence_path.unlink(missing_ok=True)
    theory, export, roots = render(original['bundle'], proposal, type_evidence_path)
    for name, content in original['bundle']['sources'].items():
        if name == 'Export.thy':
            continue
        path = project / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    original_settings = Path(original['bundle']['source_project']) / 'agent.toml'
    if original_settings.exists():
        (project / 'agent.toml').write_bytes(original_settings.read_bytes())
    (project / 'Optimization.thy').write_text(theory)
    (project / 'Source_Guard.ML').write_text(source_guard(proposal))
    (project / 'Export.thy').write_text(export)
    save(project / 'case.json', {'id': original['bundle']['case']})
    bundle = preprocess(project, cfg, directory / 'extraction', executor)
    if set(bundle['source_model']['entries']) != set(roots.values()):
        raise Failure('source_export_changed', 'Extracted exports differ from the proved replacement roots')
    if not type_evidence_path.is_file():
        raise Failure('source_type_evidence_missing', 'Trusted source export type audit did not complete')
    type_evidence = read(type_evidence_path)
    types = checked_export_types(type_evidence, roots)
    bundle['original_source_model'] = deepcopy(original['bundle']['original_source_model'])
    bundle['source_equivalence'] = {
        'status': 'proved', 'kind': 'unconditional function equality for every original export',
        'original_to_optimized': roots, 'theory_sha256': fingerprint(theory),
        'proposal': proposal, 'directory': str(directory), 'skip_proofs': False,
        'oracle_dependencies': [], 'oracle_audit': 'root equality proofs and reachable executable code equations',
        'command_guard': 'Isabelle outer lexer with positive command allowlist',
        'export_type_preservation': types,
        'export_type_authority': 'Sign.the_const_constraint in imported original theory context',
        'export_type_evidence_sha256': fingerprint(type_evidence),
        'original_source_hashes': original['bundle']['source_hashes'],
    }
    if text_encoding is not None:
        bundle['source_equivalence']['text_encoding'] = text_encoding
    save(directory / 'proof.json', bundle['source_equivalence'])
    return bundle


def rebase(original, incumbent, bundle):
    """Update source graph/partition and map roots; preserve the public Rust API.

New helper mappings and implementation choices are supplied by the translator
after it sees the extracted graph. Old decisions remain in provenance/history.
"""
    state = deepcopy(incumbent); model = bundle['source_model']
    roots = bundle['source_equivalence']['original_to_optimized']
    previous_roots = incumbent['bundle'].get('source_equivalence', {}).get('original_to_optimized', {})
    remap = {previous_roots.get(old, old): new for old, new in roots.items()}
    reachable = set(graph(model)['edges']); mandatory = project_functions(model)
    boundaries = [r for r in original['partition']['boundaries']
                  if r['source'] in reachable and r['source'] not in mandatory]
    state['partition'] = partition(model, boundaries)
    mapping = []
    for row in state['mapping']:
        row = deepcopy(row); row['source'] = remap.get(row['source'], row['source'])
        if row['source'] in model['entities']:
            mapping.append(row)
    state['mapping'] = mapping; state['bundle'] = bundle
    strategy = deepcopy(state['implementation_strategy']); decisions = []
    for row in strategy['decisions']:
        revised = deepcopy(row)
        revised['sources'] = [remap.get(n, n) for n in row['sources']
                              if remap.get(n, n) in model['entities']]
        if revised != row or (row['sources'] and not revised['sources']):
            strategy['history'].append(row)
            revised['revision'] += 1; revised['status'] = 'needs_review'
        if not row['sources'] or revised['sources']:
            decisions.append(revised)
    strategy['decisions'] = decisions; strategy['revision'] += 1
    state['implementation_strategy'] = strategy
    state['completed'] = []; state['reviews'] = {}; state['unit'] = None
    state['source_transition'] = {
        'previous_source': fingerprint(incumbent['bundle']['source_model']),
        'source': fingerprint(model), 'root_mapping': remap,
        'required_translation_units': state['partition']['order'],
        'proof': bundle['source_equivalence'],
    }
    return state


def source_context(state):
    model = state['bundle']['source_model']
    sources = set(state['partition']['owner']) | {r['source'] for r in state['mapping']}
    return {'entries': model['entries'],
            'entities': [readable(model['entities'][n]) for n in sorted(sources) if n in model['entities']],
            'boundaries': state['partition']['boundaries'],
            'units': state['partition']['units'],
            'dependency_order': state['partition']['order'],
            'source_equivalence': state['bundle'].get('source_equivalence')}
