"""Mode-neutral baseline findings, separate from candidate-change admission.

No model stage, proof, global cache or baseline mutation. Existing admission
reports carry findings; final sealing preserves all valid reviews, including
rejections. A declared violation holds the whole Off/Rust-only/Full case;
unproved inherited concerns do not silently strengthen baseline qualification.
"""
from copy import deepcopy
from pathlib import Path
from .common import Failure, digest, read
from .task_context import fingerprint
from .translation_workflow import version

POLICY = 'baseline-quality-separate-from-candidate-scope-v2'
MODES = ['off', 'rust-only', 'full']
CLAIM_LIMIT = 'Frozen source/differential validation is executed evidence, not a mathematical proof of all inputs or undeclared standalone helper APIs.'


def validation_context(original):
    support = original.get('support_evidence', {})
    suites = original.get('differential_suites', [])
    facts = {'source_test_status': support.get('status', 'not_supplied'),
             'source_tests_identity': support.get('frozen_identity'),
             'differential_statuses': [r.get('status', 'not_supplied') for r in suites],
             'validation_evidence_sha256': fingerprint({'source': support, 'differential': suites})}
    binding = {'candidate_version': version(original),
               'source_model_sha256': fingerprint(original['bundle']['source_model']),
               'numeric_policy_sha256': fingerprint(original['bundle'].get('numeric_policy', {})),
               'connector_sha256': fingerprint(original.get('connector', {})),
               'validation_facts': facts}
    return {'baseline_id': fingerprint(binding), 'binding': binding,
            'declared_source_exports': list(original['bundle']['source_model']['entries']),
            'source_ids': sorted(original['bundle']['source_model']['entities']),
            'claim_limit': CLAIM_LIMIT,
            'responsibility': 'Historical validation facts from the frozen original, qualified by the existing correctness workflow. Candidate scope reviews changed/activated obligations and current business computation. A reported inherited violation affecting a declared root holds all three modes; an unknown or missing all-input proof is recorded, not a new baseline admission requirement.'}


def findings(review, baseline):
    rows = review.get('inherited_baseline_findings', [])
    if not isinstance(rows, list):
        raise Failure('invalid_scope_review', 'Inherited baseline findings must be an array')
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('status'), str) or
                row['status'] not in {'violated', 'unknown', 'claim_limit'} or
                not isinstance(row.get('declared_root_impact'), str) or
                row['declared_root_impact'] not in {'affected', 'unknown', 'not_affected'} or
                any(not isinstance(row.get(k), str) or not row[k].strip() for k in ['finding', 'evidence'])):
            raise Failure('invalid_scope_review', 'Baseline findings need status, root applicability and source/code evidence')
        ids = row.get('source_ids')
        if (not isinstance(ids, list) or not ids or
                any(not isinstance(n, str) or n not in baseline['source_ids'] for n in ids)):
            raise Failure('invalid_scope_review', 'Baseline findings must cite original source IDs')
    return deepcopy(rows)


def summarize(baseline, rows, report_links=()):
    unique = {fingerprint(row): row for row in rows}
    rows = [unique[k] for k in sorted(unique)]
    return {'schema': 1, 'policy': POLICY, 'baseline_validation': deepcopy(baseline),
            'inherited_baseline_findings': rows,
            'publication_hold': any(r['status'] == 'violated' and r['declared_root_impact'] != 'not_affected' for r in rows),
            'unresolved_inherited_concerns': [r for r in rows if r['status'] == 'unknown'],
            'affected_modes': MODES,
            'claim_limits': [CLAIM_LIMIT] + [r['finding'] for r in rows if r['declared_root_impact'] == 'not_affected'],
            'admission_reports': list(report_links),
            'claim': 'The original correctness workflow qualifies the frozen baseline. Unknown inherited concerns remain visible and are not proofs of either correctness or a defect. Reported violations affecting declared roots hold Off, Rust-only and Full uniformly; candidate repairs do not clear them. Candidate-introduced uncertainty remains subject to the separate strict admission gate.'}


def collect_admissions(original, attempts):
    baseline = validation_context(original); rows = []; links = []
    for attempt in attempts:
        link = attempt.get('scope_admission')
        if not link:
            # Rejected valid reviews have a sealed link in Failure.evidence.
            evidence = attempt.get('error', {}).get('evidence')
            if isinstance(evidence, dict) and evidence.get('review_sha256'):
                link = {'path': evidence.get('review'), 'sha256': evidence['review_sha256']}
        if not link:
            continue  # No valid review: do not promote malformed findings.
        path = Path(link['path'])
        if not path.is_file() or digest(path) != link.get('sha256'):
            raise Failure('optimization_admission_changed', str(path))
        report = read(path)
        if report.get('baseline_validation') != baseline:
            raise Failure('optimization_baseline_quality_changed', str(path))
        rows.extend(findings(report['review'], baseline))
        links.append({'path': str(path), 'sha256': digest(path)})
    return summarize(baseline, rows, links)


def merge_selected(original, selections):
    """Consume sealed mode reports, never trust a detached result-only finding."""
    baseline = validation_context(original); rows = []; links = []
    for mode, result in selections.items():
        # selected-state.json and scope-review are fixed siblings in each run.
        path = Path(result['selected_state']).parent / 'scope-review/review.json'
        expected = result.get('scope_selection', {}).get('review_sha256')
        if not path.is_file() or digest(path) != expected:
            raise Failure('optimization_scope_review_changed', str(path))
        quality = read(path).get('baseline_quality')
        if quality is None and 'baseline_quality' not in result:
            continue  # Completed legacy reports remain read-only compatible.
        if isinstance(quality, dict) and quality.get('policy') != POLICY:
            raise Failure('optimization_baseline_quality_policy_changed',
                          'Keep historical reports unchanged; use fresh optimization runs under the same current policy for a new comparison')
        if not isinstance(quality, dict) or quality != result['baseline_quality'] or quality.get('baseline_validation') != baseline:
            raise Failure('optimization_baseline_quality_changed', mode)
        # Re-derive hold flags; a false flag cannot erase a negative finding.
        validated_findings = findings({'inherited_baseline_findings': quality.get('inherited_baseline_findings')}, baseline)
        actual = summarize(baseline, validated_findings, quality.get('admission_reports', []))
        if quality != actual:
            raise Failure('optimization_baseline_quality_changed', mode)
        rows.extend(quality['inherited_baseline_findings'])
        links.append({'mode': mode, 'path': str(path), 'sha256': expected})
    return summarize(baseline, rows, links)
