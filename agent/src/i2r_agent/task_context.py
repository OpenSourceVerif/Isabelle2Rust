"""Versioned, trial-local evidence and bounded working conversations.

The archive is authoritative. A conversation is a disposable view, never a
cross-task memory or a substitute for source equations and executed checks.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .common import ROOT, Failure, read, save


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def enabled(cfg):
    return cfg.get('context_management', {}).get('enabled', False)


class Archive:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def put(self, kind, value):
        version = kind + '-' + fingerprint(value)
        path = self.directory / (version + '.json')
        if not path.exists():
            save(path, value)
        return version

    def get(self, version):
        if not re.fullmatch(r'[a-z]+-[0-9a-f]{64}', version):
            raise Failure('unknown_material', 'Use an exact material version from the catalog', version)
        path = self.directory / (version + '.json')
        if not path.exists():
            raise Failure('unknown_material', 'Material version is not in this trial', version)
        value = read(path)
        if version.split('-', 1)[1] != fingerprint(value):
            raise Failure('material_changed', 'Archived evidence hash mismatch', version)
        return value


def register(bundle, directory, files=None):
    previous_archive = bundle.get('_context_archive')
    archive = Archive(directory)
    bundle['_context_archive'] = str(archive.directory)
    original = bundle.get('original_programs', bundle['programs'])
    versions = {'G0': archive.put('graph', original), 'current': archive.put('graph', bundle['programs'])}
    loaded = bundle.get('loaded_adapter') or bundle.get('base_adapter') or {}
    if loaded.get('before_target'):
        versions['before_target'] = archive.put('graph', [loaded['before_target']])
    bundle['graph_versions'] = versions
    # Capture available source text once. Later reads never follow a changing
    # external file instead of the source version used to make this candidate.
    if 'source_versions' not in bundle:
        sources = dict(bundle.get('sources', {}))
        for item in bundle.get('source_catalog', []):
            path = item.get('path')
            if path and item.get('available') and path not in sources and Path(path).is_file():
                sources[path] = Path(path).read_text()
        bundle['source_versions'] = {name: archive.put('source', text) for name, text in sources.items()}
    else:
        # Prepared analysis and generation use different archive directories.
        # Carry immutable captured source objects forward, never reread today's
        # external files under an old version/name. Missing/corrupt evidence is
        # a hard failure, including on restored checkpoints.
        for name,source_version in bundle['source_versions'].items():
            if not isinstance(source_version,str) or not re.fullmatch(r'source-[0-9a-f]{64}',source_version):
                raise Failure('unknown_material','Invalid frozen source identity',name)
            if (archive.directory/(source_version+'.json')).exists():
                archive.get(source_version)
            else:
                if not previous_archive:
                    raise Failure('unknown_material','Prepared source archive is missing; do not reread external sources',name)
                text=Archive(previous_archive).get(source_version)
                if archive.put('source',text)!=source_version:
                    raise Failure('material_changed','Captured source type/hash mismatch',name)
    result = {'graphs': versions, 'sources': bundle['source_versions'],
              'bindings_version': archive.put('bindings', loaded.get('bindings', {}))}
    if 'source_model' in bundle:
        bundle['model_versions'] = {'original': archive.put('model', bundle.get('original_source_model', bundle['source_model'])),
                                    'current': archive.put('model', bundle['source_model'])}
        result['models'] = bundle['model_versions']
    if files is not None:
        result['code_version'] = archive.put('code', files)
    return result


def reference_catalog():
    from .repair_knowledge import CATALOG
    return [{'path': str(Path(CATALOG).relative_to('skills')), 'version': fingerprint((ROOT / CATALOG).read_text()), 'kind': 'bounded_advisory_catalog'}]+ [{'path': str(p.relative_to(ROOT / 'skills')), 'version': fingerprint(p.read_text())}
            for name in ['semantic-adaptation', 'rust-generation']
            for p in sorted((ROOT / 'skills' / name / 'references').glob('*.md'))]


def graph_nodes(bundle, version='current'):
    version = bundle['graph_versions'].get(version, version)
    graphs = Archive(bundle['_context_archive']).get(version)
    if not version.startswith('graph-'):
        raise Failure('invalid_material_type', 'Expected graph version')
    return version, {n['id']: n for graph in graphs for n in graph['nodes']}


def validate_source_requests(reply):
    requests=reply.get('request_sources',[])
    if not isinstance(requests,list) or any(not isinstance(r,dict) or not isinstance(r.get('path'),str) or not r['path'] for r in requests):
        raise Failure('invalid_source_request','request_sources must be an array of objects with path, not an array of path strings',
                      {'reply_shape':{'request_sources':[{'path':'EXACT_SOURCE_CATALOG_PATH','start_line':1,'end_line':1}]},
                       'instruction':'Copy path from the current source catalog. start_line/end_line are one-based inclusive; source_version, when supplied, must match the current source version. No source text is accepted in the request.'})


def read_material(reply, bundle, files=None):
    validate_source_requests(reply)
    archive = Archive(bundle['_context_archive'])
    reply = deepcopy(reply)
    if 'source_model' in bundle:
        # Legacy read names are accepted without feeding a Thingol program back
        # into a new-model conversation.
        requests = reply.setdefault('request_entities', [])
        for item in reply.pop('request_nodes', []):
            item = {'id': item} if isinstance(item, str) else item
            label = 'original' if item.get('graph_version') == 'G0' else 'current'
            if item['id'] in bundle['source_model']['entities'] or item['id'] in bundle.get('original_source_model', {}).get('entities', {}):
                requests.append({'id': item['id'], 'model_version': label})
            else:
                raise Failure('backend_symbol_not_source', 'This is a backend compatibility identifier; request its source type/class/operations or binding evidence, not a Thingol definition', item)
        for label in reply.pop('request_graphs', []):
            label = 'original' if label == 'G0' else label
            version = bundle['model_versions'].get(label)
            if version is None:
                raise Failure('invalid_material_type', 'Use original/current source model')
            model = archive.get(version)
            requests.extend({'id': n, 'model_version': version} for n in model['entities'])
    result = {}
    for request in reply.get('request_entities', []):
        request = {'id': request} if isinstance(request, str) else request
        version = bundle.get('model_versions', {}).get(request.get('model_version', 'current'), request.get('model_version', 'current'))
        if not version.startswith('model-'):
            raise Failure('invalid_material_type', 'Expected a source model version')
        model = archive.get(version)
        symbol = request['id']
        if symbol not in model['entities']:
            raise Failure('unknown_source_symbol', 'Choose an entity in the source model catalog', request)
        ids = {symbol}
        if request.get('include_callers'):
            ids.update(model['entities'][symbol]['callers'])
        if request.get('include_dependencies'):
            from .program_model import reachable
            ids.update(reachable(model, [symbol]))
        result.setdefault('entities', []).extend({'model_version': version, **model['entities'][n]} for n in sorted(ids) if n in model['entities'])
        result.setdefault('uses', []).extend(u for u in model['uses'] if u['caller'] in ids or u['callee'] == symbol)
    for version in reply.get('request_materials', []):
        if not version.startswith(('reads-', 'event-', 'decisions-', 'catalog-', 'turn-', 'bindings-')):
            raise Failure('invalid_material_type', 'Use an archived reading/repair-event version')
        result.setdefault('materials', {})[version] = archive.get(version)
    for request in reply.get('request_nodes', []):
        request = {'id': request, 'graph_version': 'current'} if isinstance(request, str) else request
        version, nodes = graph_nodes(bundle, request.get('graph_version', 'current'))
        symbol = request['id']
        if symbol not in nodes:
            raise Failure('unknown_source_symbol', 'Choose a symbol in the specified graph; use G0 for adapted-away nodes', request)
        result.setdefault('nodes', []).append({**nodes[symbol], 'graph_version': version})
    for request in reply.get('request_graphs', []):
        version = bundle['graph_versions'].get(request, request)
        if not version.startswith('graph-'):
            raise Failure('invalid_material_type', 'Expected graph version')
        from .generation import intern_program
        result.setdefault('graphs', {})[version] = intern_program(archive.get(version))
    for request in reply.get('request_sources', []):
        name = request['path']
        version = bundle['source_versions'].get(name)
        if version is None:
            raise Failure('unknown_source_path', 'Choose a source catalog path', name)
        if request.get('source_version', version) != version:
            raise Failure('stale_source_version', 'Source version does not match this trial', name)
        result.setdefault('sources', []).append(excerpt(name, archive.get(version), request, version))
    for request in reply.get('request_files', []):
        version = request.get('code_version')
        content = archive.get(version) if version else files
        if version and not version.startswith('code-'):
            raise Failure('invalid_material_type', 'Expected code version')
        name = request['path']
        if content is None or name not in content:
            raise Failure('unknown_code_file', 'Choose a current file catalog path', name)
        version = version or archive.put('code', content)
        result.setdefault('files', []).append(excerpt(name, content[name], request, version))
    if reply.get('request_references'):
        from .knowledge import references
        result['references'] = references(reply['request_references'])
    return result


def excerpt(name, text, request, version):
    lines = text.splitlines()
    start, end = int(request.get('start_line', 1)), int(request.get('end_line', len(lines)))
    if start < 1 or end < start or start > max(1, len(lines)):
        raise Failure('invalid_source_range', 'Use a valid one-based inclusive line range', request)
    end = min(end, len(lines))
    return {'path': name, 'version': version, 'start_line': start, 'end_line': end,
            'text': '\n'.join(lines[start - 1:end])}


def merge_material(previous, additions):
    """Keep reads by identity/version, not just by symbol or last request."""
    result = deepcopy(previous or {})
    for key, value in additions.items():
        if isinstance(value, dict):
            result[key] = {**result.get(key, {}), **value}
        elif isinstance(value, list):
            indexed = {fingerprint(v): v for v in result.get(key, []) + value}
            result[key] = list(indexed.values())
        else:
            result[key] = value
    return result


def selected_files(files, feedback, limit=45000):
    catalog = {name: {'sha256': fingerprint(text), 'lines': len(text.splitlines()),
                     'items': re.findall(r'(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:fn|struct|enum|type|trait|mod)\s+[^\n{;]+', text)}
               for name, text in files.items()}
    if sum(map(len, files.values())) <= limit:
        return deepcopy(files), catalog, []
    diagnostic = json.dumps(feedback or {}, ensure_ascii=False)
    selected, ranges = {}, []
    for name, text in files.items():
        hits = [int(x) for x in re.findall(re.escape(name) + r':(\d+)', diagnostic)]
        if len(text) <= 6000 or (name in diagnostic and len(text) <= limit // 2):
            selected[name] = text
        elif hits:
            lines = text.splitlines()
            for line in sorted(set(hits))[:8]:
                ranges.append(excerpt(name, text, {'start_line': max(1, line - 35), 'end_line': min(len(lines), line + 45)}, fingerprint(text)))
    return selected, catalog, ranges


def source_evidence(bundle, selected, feedback, review=False, limit=32000):
    """Seed local repair with original equations, including removed G1 nodes."""
    if 'source_model' in bundle:
        from .program_model import view, focused_ids
        return view(bundle, focused_ids(bundle, {'feedback': feedback}), original=True)
    version, nodes = graph_nodes(bundle, 'G0')
    text = json.dumps({'code': selected, 'failure': feedback}, ensure_ascii=False)
    entries = {e for graph in bundle.get('original_programs', bundle['programs']) for e in graph['entries']}
    names = [n for n in nodes if n in entries]
    names += [n for n in nodes if n not in entries and re.search(r'\b' + re.escape(n.rsplit('.', 1)[-1].split(':')[-1]) + r'\b', text)]
    rows, used = [], 0
    for name in names:
        n = nodes[name]
        size = len(json.dumps(n, ensure_ascii=False))
        if used + size > limit:
            continue
        rows.append({**n, 'graph_version': version})
        used += size
    from .generation import intern_program
    return {'graph_version':version, 'selected_equations':intern_program([{'entries':[n for n in entries if n in {r['id'] for r in rows}], 'nodes':rows}]), 'selection': 'Original entries and names occurring in current evidence; heuristic, request missing dependencies explicitly.',
            'available_original_symbols': list(nodes), 'provided_symbols': [r['id'] for r in rows]}


class Conversation:
    def __init__(self, path, cfg):
        self.path = Path(path)
        self.cfg = cfg
        self.state = read(self.path) if self.path.exists() else {'scope': None, 'turns': [], 'compactions': 0}
        self.archive = Archive(self.path.parent / 'materials')

    def enter(self, scope):
        options = self.cfg.get('context_management', {})
        history_size = len(json.dumps(self.state['turns'], ensure_ascii=False))
        if self.state['scope'] != scope:
            self.state.update(scope=scope, turns=[], graph_sent=False, compactions=self.state['compactions']+1)
        limit=options.get('max_history_turns',4)
        while self.state['turns'] and (len(self.state['turns'])>limit or len(json.dumps(self.state['turns'],ensure_ascii=False))>options.get('history_characters',90000)):
            self.state['turns'].pop(0)
            self.state['compactions']+=1
        return not self.state['turns']

    def has_graph(self):
        return self.state.get('graph_sent',False) or any(t.get('full_graph') for t in self.state['turns'])

    def call(self, provider, system, payload, directory, phase='generation', options=None):
        messages = [{'role': 'system', 'content': system}]
        for turn in self.state['turns']:
            messages.extend(turn['messages'])
        prompt = json.dumps(payload, ensure_ascii=False)
        messages.append({'role': 'user', 'content': prompt})
        size = sum(len(m['content']) for m in messages)
        cap = self.cfg['preprocessing']['max_context_chars']
        # Exact source is not silently clipped. Compact retained conversation,
        # as a cost hint. In correctness-only, the provider alone decides whether
        # the complete current request fits; no local character rejection.
        if size > cap and self.state['turns']:
            messages = [messages[0], messages[-1]]
            self.state['turns'] = []
            self.state['compactions'] += 1
            size = sum(len(m['content']) for m in messages)
        if size > cap and not self.cfg.get('v8',{}).get('correctness_only'):
            raise Failure('context_budget_exceeded', 'Current material exceeds the context limit; no silent truncation')
        save(Path(directory) / 'conversation-audit.json', {'scope': self.state['scope'], 'message_count': len(messages),
             'characters': size, 'current_characters': len(prompt), 'compactions': self.state['compactions'],
             'full_graph': 'thingol' in payload.get('program', {}),
             'source_model_view': 'program_model' in payload.get('program', {}), 'current_code_version': payload.get('code_version')})
        reply = provider.call(system, prompt, options=options, phase=phase, messages=messages)
        if not isinstance(reply, dict):
            raise Failure('invalid_model_response', 'Expected JSON object')
        if any(k in payload.get('program',{}) for k in ['thingol','program_model']):self.state['graph_sent']=True
        exact_turn = {'request':payload, 'response':reply}
        version=self.archive.put('turn', exact_turn)
        # Retain reasoning/actions and execution outcome, not a second copy of
        # graphs, files, diagnostics and catalogs in every history turn.
        reply_record={k:reply[k] for k in ['action','diagnosis','notes','decisions','request_nodes','request_entities','request_files','request_sources'] if k in reply}
        if reply.get('edits') or reply.get('files'):
            reply_record['proposed_patch']={'base_code_version':reply.get('base_code_version'),
                'edit_files':[e.get('file') for e in reply.get('edits',[]) if isinstance(e,dict)] if isinstance(reply.get('edits',[]),list) else [],
                'replacement_files':list(reply['files']) if isinstance(reply.get('files'),dict) else [],
                'exact_response':version}
        if len(json.dumps(reply_record,ensure_ascii=False))>6000:
            reply_record={'action':reply.get('action'),'details_in_archive':version}
        record={'previous_action':reply_record,'response_archive':version,
                'controller_state':payload.get('controller_state'),
                'issue_id':payload['feedback'].get('issue_id') if isinstance(payload.get('feedback'),dict) else None,
                'notice':'Previous response is a proposal. Current files and executed checks are authoritative; exact prior material is archived.'}
        self.state['turns'].append({'full_graph':'thingol' in payload.get('program',{}),
            'messages':[{'role':'user','content':json.dumps({k:v for k,v in record.items() if k!='previous_action'},ensure_ascii=False)},
                        {'role':'assistant','content':json.dumps(reply_record,ensure_ascii=False)}]})
        save(self.path, self.state)
        return reply


def prepare_generation(branch, payload, cfg, work):
    bundle = branch['bundle']
    versions = register(bundle, Path(work) / 'context/materials', branch['files'])
    mode = ('review' if branch['mode'] == 'review' else 'repair' if 'src/lib.rs' in branch['files'] else
            'adapt-repair' if (branch.get('feedback') or {}).get('status','').startswith('adapter') else
            'generate' if bundle.get('loaded_adapter') else 'adapt')
    session = Conversation(Path(work) / 'context' / (branch['id'] + '.json'), cfg)
    session.enter(mode + ':' + versions.get('models', versions['graphs'])['current'])
    program = payload['program']
    program.pop('source_catalog',None) # exact source paths and versions are in material_versions
    full = mode in {'adapt', 'generate'} and not session.has_graph()
    if not full:
        program.pop('thingol', None)
        program.pop('sources', None)
    selected, catalog, excerpts = selected_files(branch['files'], branch.get('feedback'), cfg.get('context_management', {}).get('code_characters', 45000))
    if mode == 'review':
        selected, excerpts = deepcopy(branch['files']), []
    payload['current_files'] = selected
    payload['file_catalog'], payload['file_excerpts'] = catalog, excerpts
    payload['code_version'] = versions['code_version']
    source_catalog=Archive(bundle['_context_archive']).put('catalog',versions['sources'])
    payload['material_versions'] = {k:v for k,v in versions.items() if k!='sources'}
    payload['material_versions']['source_catalog']=source_catalog
    payload['material_versions']['source_paths']=list(bundle.get('sources',{}))
    payload['material_versions']['source_catalog_instruction']='Read source_catalog through request_materials to enumerate all frozen paths.'
    program['reading_protocol'] = ('Complete current graph is supplied for initial adaptation/generation. Repair and review use selected evidence. '
        'Original graph/source, omitted Rust bodies and named references remain readable by exact version. '
        'Latest controller state and current_files supersede earlier drafts. A catalog/hash alone is not the contents.')
    program['reference_catalog'] = reference_catalog()
    program['requested_material'] = branch.get('pending_material', {})
    archive = Archive(bundle['_context_archive'])
    payload['read_material_version'] = archive.put('reads', branch.get('extra', {}))
    # Adaptation is a legal action during any repair/review. Always publish its
    # actual version; otherwise a model can only invent or reuse a stale hash.
    from .repair_state import adapter_snapshot
    adapter_files=adapter_snapshot({**branch, 'plan': branch.get('plan', {'adapter': {}})})
    payload['base_adapter_version']=archive.put('code',adapter_files)
    payload['adapter_files'],payload['adapter_file_catalog'],payload['adapter_file_excerpts']=selected_files(adapter_files,branch.get('feedback'),45000)
    payload['adapter_body_reuse']={name:'current_files' for name,text in payload['adapter_files'].items()
                                  if branch['files'].get(name)==text}
    payload['adapter_files']={name:text for name,text in payload['adapter_files'].items() if name not in payload['adapter_body_reuse']}

    # Keep small relevant technical references across source/code reads and stage transitions.
    from .knowledge import references
    topics=['semantic-adaptation/references/numeric-semantics.md']
    evidence=json.dumps({'files':selected,'feedback':branch.get('feedback')})
    if any(x in evidence for x in ['E0382','E050','E0597','Rc<','Box<']):topics.append('rust-generation/references/ownership-examples.md')
    if any(x in evidence for x in ['dyn Fn','FnMut','FnOnce',"'static"]):topics.append('rust-generation/references/closures-and-generics.md')
    if mode=='review':topics.append('rust-generation/references/structural-costs.md')
    branch['extra']=merge_material(branch.get('extra',{}),{'references':references(topics)})
    program['retained_references'] = branch['extra']['references']
    if not full:
        program['original_evidence'] = source_evidence(bundle, selected, branch.get('feedback'), mode == 'review')
    payload['repair_history_version']=archive.put('reads',branch.get('repair_history', []))
    payload['working_record'] = {'decisions': branch.get('decisions', []), 'recent_attempts': [{k:e.get(k) for k in ['attempt','action','result','changed_files','diagnosis']} for e in branch.get('repair_history', [])[-3:]],
        'active_issue':(branch.get('repair_issue') or {}).get('id'), 'notice': 'Decisions are revisable model judgments, not verified facts. Full history is archived.'}
    payload['available_actions'] += ['request_files', 'request_graphs', 'request_materials', 'revise_analysis']
    if not full:
        from .repair_state import feedback as issue_feedback
        payload['feedback']=issue_feedback(branch)
        removed={key:program.pop(key,None) for key in ['symbols','analysis','active_bindings','implementation_declarations']}
        removed['mapping']=payload.pop('current_mapping',[])
        payload['context_catalog_version']=archive.put('catalog',removed)
        # Small searchable catalog; signatures and dependencies available via nodes.
        program['symbol_index']=[x['id'] for x in (removed['symbols'] or [])]
        program['analysis_summary']={'status':'revisable recommendation','details':payload['context_catalog_version']}
        names=set(program.get('entries',[]))
        diagnostic=json.dumps(payload.get('feedback'),ensure_ascii=False)
        program['relevant_signatures']=[x for x in (removed['symbols'] or []) if x['id'] in names or x['id'].split('.')[-1] in diagnostic]
        payload['relevant_mapping']=[x for x in removed['mapping'] if x.get('source') in names]
        program['binding_evidence_version']=versions['bindings_version']
        payload['current_adapter']={k:v for k,v in payload.get('current_adapter',{}).items() if k in ['dependencies','build_dependencies','support_file_names']}
    if mode=='review':
        from .code_quality import findings
        leads=findings(branch['files'])
        payload['quality_findings']=leads[:20]
        payload['quality_findings_version']=archive.put('catalog',leads)
        payload['quality_instruction']='Inspect these leads against the actual source, not generated comments. They are not automatic defects. Before unchanged acceptance, structural leads require quality_resolutions [{id,source_operation,source_cost,rust_cost,resolution:retain|not_applicable,reason}]. Otherwise return edits. A retained extra cost needs an actual constraint, not a small observed test size. Do not attribute Vec shifts, tail collection or whole-vector cons to constant-time functional-list decomposition/cons. For important choices report conditions, source basis and tradeoffs.'
    if 'source_model' in bundle:
        from .program_model import view, focused_ids, context_record, semantic_changes
        program['program_model'] = view(bundle, focused_ids(bundle, branch))
        program.pop('original_evidence', None)
        changed_source = semantic_changes(bundle)
        program['source_changes'] = {'changed_entities': changed_source,
            'comparison': 'Exact entity facts excluding relocated file/line metadata. Complete original/current versions remain readable.'}
        if changed_source:
            program['original_evidence'] = view(bundle, changed_source, original=True)
        program['reading_protocol'] = 'Every turn supplies a fresh semantic view: source/execution equations, callers, dependency/types and binding boundaries. Full typed entities are archived under model_versions. Request missing entities with callers/dependencies explicitly. No alias/liveness fact is inferred from an occurrence edge.'
        payload['program_state'] = context_record(branch)
        payload['available_actions'] += ['request_entities']
    payload['_conversation'] = session
    return payload


def record_attempt(branch, attempt, before, reply, directory, before_adapter=None, before_issue=None, before_connector=None, before_mapping=None):
    after = branch['files']
    from .program_model import record
    record(branch, attempt, before)
    changed = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    status=attempt.get('development',{}).get('status')
    event = {'issue':before_issue or (branch.get('repair_issue') or {}).get('id'), 'attempt': attempt['attempt'], 'phase': attempt['action_phase'], 'action': attempt.get('action'),
             'before': fingerprint(before), 'after': fingerprint(after), 'changed_files': changed,
             'diagnosis': (reply or {}).get('diagnosis'), 'notes': (reply or {}).get('notes'),
             'result': attempt.get('development', {}).get('status'), 'evidence_path': str(Path(directory) / 'attempt.json')}
    if before_connector is not None:
        after_connector=branch.get('connector',{})
        event['connector_before']=fingerprint(before_connector)
        event['connector_after']=fingerprint(after_connector)
        event['changed_connector_files']=[n for n in sorted(set(before_connector)|set(after_connector)) if before_connector.get(n)!=after_connector.get(n)]
    if before_mapping is not None:
        old={r['source']:r for r in before_mapping};new={r['source']:r for r in branch.get('mapping',[])}
        event['mapping_changes']={'removed':sorted(old.keys()-new.keys()),'added':sorted(new.keys()-old.keys()),
            'updated':[n for n in sorted(old.keys()&new.keys()) if old[n]!=new[n]]}
    operation_path=Path(directory)/('connection/edit-operation.json' if attempt['action_phase']=='connect' else 'edit-operation.json')
    if operation_path.exists():event['edit_execution']=read(operation_path)
    if before_issue and any(i['id']==before_issue for i in branch.get('closed_issues',[])):
        event['issue_closed']=before_issue
    if before_adapter is not None:
        from .repair_state import adapter_snapshot
        after_adapter=adapter_snapshot(branch)
        event['changed_adapter_files']=[n for n in sorted(set(before_adapter)|set(after_adapter)) if before_adapter.get(n)!=after_adapter.get(n)]
    branch.setdefault('repair_history', []).append(event)
    attempt['repair_event'] = event
    save(Path(directory) / 'repair-event.json', event)
    import difflib
    diff = ''.join(''.join(difflib.unified_diff(before.get(name, '').splitlines(True), after.get(name, '').splitlines(True),
                    fromfile=name + ' (before)', tofile=name + ' (after)')) for name in changed)
    (Path(directory) / 'changes.diff').write_text(diff)
    if before_connector is not None:
        connector_diff=''.join(''.join(difflib.unified_diff(before_connector.get(n,'').splitlines(True),after_connector.get(n,'').splitlines(True),
            fromfile='connector/'+n+' (before)',tofile='connector/'+n+' (after)')) for n in event['changed_connector_files'])
        (Path(directory)/'connector-changes.diff').write_text(connector_diff)
    if before_adapter is not None:
        adapter_diff=''.join(''.join(difflib.unified_diff(before_adapter.get(n,'').splitlines(True),after_adapter.get(n,'').splitlines(True),fromfile=n+' (before)',tofile=n+' (after)')) for n in event['changed_adapter_files'])
        (Path(directory)/'adapter-changes.diff').write_text(adapter_diff)
    if changed:
        for decision in branch.get('decisions', []):
            # A judgment issued with this very edit is about the resulting code;
            # prior decisions remain stale until explicitly reconsidered.
            proposed = (reply or {}).get('decisions')
            supplied = {d['id'] for d in (proposed if isinstance(proposed,list) else [])
                        if isinstance(d,dict) and isinstance(d.get('id'),str)}
            decision['review_required'] = decision['id'] not in supplied
            if decision['id'] in supplied:
                decision['code_version'] = fingerprint(after)


def update_decisions(branch, reply):
    incoming = reply.get('decisions', [])
    if not isinstance(incoming, list):
        raise Failure('invalid_decisions', 'decisions must be a list')
    for decision in incoming:
        if not isinstance(decision, dict) or not decision.get('choice') or not decision.get('conditions') or not decision.get('basis'):
            raise Failure('invalid_decisions', 'Important decisions need choice, conditions and basis; no score is requested')
        if decision.get('id') is not None and not isinstance(decision['id'],str):
            raise Failure('invalid_decisions', 'A decision id must be a string')
        affected=decision.get('affected_symbols') or []
        if not isinstance(affected,list) or any(not isinstance(n,str) for n in affected):
            raise Failure('invalid_decisions', 'affected_symbols must be a list of source IDs')
        decision={**decision,'affected_symbols':affected}
        key = decision.get('id') or fingerprint(decision)[:16]
        branch['decisions'] = [d for d in branch.get('decisions', []) if d['id'] != key] + [
            {**decision, 'id': key, 'code_version': fingerprint(branch['files']), 'review_required': False,
             'source_model_version': branch.get('bundle',{}).get('model_versions',{}).get('current'),
             'evidence_status': 'model judgment; inspect cited source and actual checks'}]
