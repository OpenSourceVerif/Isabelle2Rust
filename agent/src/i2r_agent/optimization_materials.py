"""Read-only, versioned theory access for performance proof search.

The execution graph is not a theorem library. Reuse the correctness workflow's
captured source archive and range format; never substitute current disk text for
a frozen source version, or treat a retrieved lemma as an accepted new proof.
"""
from pathlib import Path
from .common import Failure, digest
from .task_context import Archive, excerpt, fingerprint, merge_material, validate_source_requests

MAX_READ_CHARACTERS = 40000
MAX_RETAINED_CHARACTERS = 120000


def catalog(bundle):
    entries = {r['path']: {k: r[k] for k in ('theory', 'path', 'sha256', 'bytes') if k in r}
               for r in bundle.get('source_catalog', []) if r.get('available')}
    for name, text in bundle.get('sources', {}).items():
        entries.setdefault(name, {'path': name, 'text_identity': fingerprint(text)})
    for name, version in bundle.get('source_versions', {}).items():
        entries.setdefault(name, {'path': name})['source_version'] = version
    return list(entries.values())


def read_sources(reply, bundle):
    validate_source_requests(reply)
    requests = reply.get('request_sources', [])
    if not requests:
        raise Failure('invalid_source_request', 'inspect requires nonempty request_sources with catalog paths and line ranges')
    allowed = {r['path']: r for r in catalog(bundle)}
    rows = []
    for request in requests:
        name = request['path']
        if name not in allowed:
            raise Failure('unknown_source_path', 'Use a path from source_material_catalog', name)
        item = allowed[name]
        version = item.get('source_version')
        if version:
            if request.get('source_version', version) != version:
                raise Failure('stale_source_version', 'Use the supplied frozen source version', name)
            text = Archive(bundle['_context_archive']).get(version)
        elif name in bundle.get('sources', {}):
            text = bundle['sources'][name]; version = 'source-' + fingerprint(text)
        else:
            if not item.get('sha256') or digest(Path(name)) != item['sha256']:
                raise Failure('source_material_changed', 'Theory no longer matches the extracted source catalog', name)
            text = Path(name).read_text(); version = 'source-' + fingerprint(text)
        rows.append(excerpt(name, text, request, version))
    if sum(len(r['text']) for r in rows) > MAX_READ_CHARACTERS:
        raise Failure('source_material_limit', 'Request narrower theory ranges; one read is limited to 40000 characters, without silent truncation')
    return {'sources': rows}


def merge(previous, additions):
    result = merge_material(previous, additions)
    if sum(len(r['text']) for r in result.get('sources', [])) > MAX_RETAINED_CHARACTERS:
        raise Failure('source_material_limit', 'Retained source excerpts are limited to 120000 characters; avoid overlapping or unnecessary ranges')
    return result


INITIAL_CHARACTERS = 24000


def initial_sources(bundle):
    """Attach bounded frozen root/direct-callee theory context before source feasibility triage.

    Short defining theories are shown whole, including nearby lemmas/comments.
    Large theories use explicit bounded windows at exported definitions. Missing
    or ambiguous locations are reported, never replaced by unverified disk text.
    """
    items = catalog(bundle)
    model = bundle['source_model']
    requests = []; unresolved = []
    frontier = list(model['entries'])
    for root in model['entries']:
        frontier.extend(key for key in model['entities'][root].get('dependencies', [])
                        if key in model['entities'] and key not in frontier)
    for root in frontier:
        entity = model['entities'][root]
        for spec in entity.get('specifications', []):
            location = spec.get('file'); line = spec.get('line')
            if not isinstance(location, str): continue
            suffix = location[2:] if location.startswith('~~/') else location
            matches = [r for r in items if r['path'] == location or
                       (suffix.startswith('/') and r['path'].endswith(suffix))]
            if not matches:
                candidates = [r for r in items if Path(r['path']).name == Path(location).name]
                if len(candidates) == 1: matches = candidates
            if len(matches) != 1:
                unresolved.append({'root': root, 'file': location, 'reason': 'missing_or_ambiguous_catalog_path'})
                continue
            requests.append({'path': matches[0]['path'], 'line': line, 'root': root})
        # Some derived exports lack position metadata; a unique theory namespace
        # is a deterministic fallback, not a search for performance hints.
        if not any(r['root'] == root for r in requests):
            prefix = entity.get('name', root.split(':',1)[-1]).split('.')[0]
            matches = [r for r in items if r.get('theory','').split('.')[-1] == prefix]
            if len(matches) == 1: requests.append({'path': matches[0]['path'], 'line': 1, 'root': root})
            else: unresolved.append({'root': root, 'reason': 'no_unique_defining_theory'})
    result = {}; used = 0; seen = set(); selections = []
    for request in requests:
        name = request['path']
        if name in seen: continue
        if len(seen) >= 3:
            unresolved.append({'path': name, 'reason': 'initial_theory_count_cap'});continue
        seen.add(name)
        item = next(r for r in items if r['path'] == name)
        if item.get('source_version'):
            text = Archive(bundle['_context_archive']).get(item['source_version'])
        elif name in bundle.get('sources', {}): text = bundle['sources'][name]
        else:
            if not item.get('sha256') or digest(Path(name)) != item['sha256']:
                raise Failure('source_material_changed', 'Theory no longer matches the extracted source catalog', name)
            text = Path(name).read_text()
        lines = text.splitlines(); available = INITIAL_CHARACTERS - used
        if available <= 0:
            unresolved.append({'path': name, 'reason': 'initial_context_cap'});continue
        if len(text) <= available:
            start = 1; end = max(1,len(lines)); scope = 'complete_theory'
        else:
            anchor = request['line'] if isinstance(request['line'],int) and request['line'] > 0 else 1
            start = min(len(lines),anchor);end = start;scope = 'definition_window'
            if not start or len(lines[start-1]) > available:
                unresolved.append({'path':name,'reason':'definition_line_exceeds_context_cap'});continue
            while end < min(len(lines),anchor+120) and len('\n'.join(lines[start-1:end+1])) <= available: end += 1
            while start > max(1,anchor-40) and len('\n'.join(lines[start-2:end])) <= available: start -= 1
        addition = read_sources({'request_sources':[{'path':name,'start_line':start,'end_line':end}]},bundle)
        result = merge(result,addition);used += sum(len(x['text']) for x in addition['sources'])
        selections.append({'path':name,'root':request['root'],'coverage':scope,'start_line':start,'end_line':end})
    return result, {'policy':'bounded_frozen_export_theory_context_v1','character_cap':INITIAL_CHARACTERS,'theory_cap':3,
                    'characters':used,'selections':selections,'unavailable':unresolved,
                    'rule':'The source-stage skip decision must consider these defining theories and available proof facts. If a proof-cost estimate depends on missing facts, use inspect before treating that estimate as established. No source change is required when no useful direction is found.'}
