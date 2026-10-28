#!/usr/bin/env python3
"""Read-only integrity checks for the transferred, incomplete frozen scan."""
import collections
import json
from pathlib import Path

import afp_common as common
from scan_store import Store, aggregate, file_digest, load_snapshot


def verify(scan, inventory, expected=None):
    """Validate every byte and joint receipt facts without publishing a checkpoint."""
    scan = Path(scan).resolve()
    rows = [json.loads(line) for line in Path(inventory).read_text().splitlines()]
    actual = {str(p.relative_to(scan)) for p in scan.rglob('*') if p.is_file()}
    if actual != {r['path'] for r in rows} or len(rows) != len(actual):
        raise ValueError('Frozen file inventory differs (including duplicate paths)')
    for row in rows:
        path = scan / row['path']
        if (not path.resolve().is_relative_to(scan) or path.is_symlink()
                or path.stat().st_size != row['bytes'] or file_digest(path) != row['sha256']):
            raise ValueError('Missing or changed frozen evidence: ' + row['path'])
    result, exports = load_snapshot(scan)
    data = common.read_json(scan / 'manifest.json')
    units = common.read_json(scan / 'units.json')
    derived, scope = aggregate(Store(scan), data, units, result['environment'])
    if scope != exports or any(derived['entries'][e]['scan'] != r['scan']
                              for e, r in result['entries'].items()):
        raise ValueError('Joint snapshot differs from committed session receipts')
    if (common.read_json(scan / 'exports.json') != exports or
            common.read_json(scan / 'results.json')['entries'] != result['entries']):
        raise ValueError('Compatibility views differ from the joint snapshot')
    counts = dict(collections.Counter(r['scan']['status'] for r in result['entries'].values()))
    facts = {'entries': len(data['entries']), 'sessions': len(units), 'scan_counts': counts,
             'distinct_candidates': len({c for v in exports.values() for c in common.candidates(v)}),
             'candidate_references': sum(len(common.candidates(v)) for v in exports.values())}
    for key, value in (expected or {}).items():
        if facts.get(key) != value:
            raise ValueError('Frozen fact differs: ' + key)
    return dict(facts, files=len(rows), bytes=sum(r['bytes'] for r in rows),
                snapshot=common.read_json(scan / 'scan-current.json'),
                scan_checkpoint_passed=common.read_json(scan / 'scan-checkpoint.json')['passed'],
                passed=True)


def verify_sources(scan, afp, isabelle):
    """Installation roots may differ; source names and content must stay exact."""
    inputs = common.read_json(Path(scan) / 'source-inputs.json')
    roots = {'afp': Path(afp) / 'thys', 'isabelle_src': Path(isabelle).resolve().parent.parent / 'src'}
    changes = []
    for kind, root in roots.items():
        expected = inputs[kind]
        names = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
        changes.extend(kind + ': unexpected ' + n for n in sorted(names - set(expected)))
        for name, sha in expected.items():
            p = root / name
            if not p.is_file() or file_digest(p) != sha:
                changes.append(kind + ': missing/changed ' + name)
    if changes:
        raise ValueError('Source identity mismatch:\n' + '\n'.join(changes))
    return {kind: len(inputs[kind]) for kind in roots}


EXPECTED = {'entries': 893, 'sessions': 922,
            'scan_counts': {'passed': 662, 'failed': 3, 'blocked': 228},
            'distinct_candidates': 157623, 'candidate_references': 163502}
