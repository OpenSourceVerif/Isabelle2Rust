"""Candidate scope and inherited baseline publication responsibility stay separate."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json

import pytest

from i2r_agent.common import Failure, read, save, digest
from i2r_agent import optimization as opt, optimization_scope as scope
from i2r_agent import optimization_baseline_quality as quality, optimization_matrix as matrix
import i2r_agent

# Reuse the existing deterministic full-controller fixture without copying its
# fake compiler/prover/timing implementation or changing production tests.
path = Path(i2r_agent.__path__[-1]).parents[1]/'tests/test_optimization_controller.py'
spec = importlib.util.spec_from_file_location('_baseline_controller_fixture', path)
fixture_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture_module)
controller = fixture_module.controller
rust = fixture_module.rust


def finding(impact='unknown', status='violated'):
    return {'source_ids': ['constant:Base.f'], 'status': status, 'declared_root_impact': impact,
            'obligation_kind': 'observable_semantics',
            'finding': ('Original helper contradicts a declared source obligation.' if status == 'violated'
                        else 'Inherited helper domain was not proved for all raw inputs.'),
            'evidence': ('A direct source/code mismatch is recorded for the original helper; the candidate keeps it unchanged.'
                         if status == 'violated' else 'No counterexample is supplied; original and candidate keep the same helper and use.')}


def inject_findings(monkeypatch, answers):
    original = opt.Provider
    class Reviewer(original):
        def call(self, *args, **kwargs):
            reply = super().call(*args, **kwargs)
            if kwargs.get('phase') == 'performance_scope_admission':
                reply['reviews'][0]['inherited_baseline_findings'] = deepcopy(answers.pop(0))
            return reply
    monkeypatch.setattr(opt, 'Provider', Reviewer)


def test_inherited_uncertainty_does_not_requalify_already_validated_baseline(controller, monkeypatch):
    c = controller; inject_findings(monkeypatch, [[finding(status='unknown')]])
    result = c['run']([rust('ownership change'), {'action': 'finish'}], mode='rust-only')
    assert result['attempts'][0]['status'] == 'accepted'
    assert result['improved']
    audit = read(c['directory']/'scope-review/review.json')
    assert audit['reviews'][0]['decision'] == 'within_scope'
    assert result['baseline_quality'] == audit['baseline_quality']
    assert not audit['baseline_quality']['publication_hold']
    assert audit['baseline_quality']['unresolved_inherited_concerns'] == [finding(status='unknown')]
    assert audit['baseline_quality']['affected_modes'] == ['off', 'rust-only', 'full']


@pytest.mark.parametrize('impact', ['affected', 'unknown'])
def test_reported_violation_holds_all_modes_but_missing_proof_does_not(controller, impact):
    baseline = quality.validation_context(controller['original'])
    uncertain = finding(impact, 'unknown')
    limit = finding(impact, 'claim_limit')
    violation = finding(impact, 'violated')
    for row in [uncertain, limit]:
        summarized = quality.summarize(baseline, [row])
        assert not summarized['publication_hold']
        assert summarized['inherited_baseline_findings'] == [row]
    held = quality.summarize(baseline, [uncertain, violation])
    assert held['publication_hold'] and held['affected_modes'] == quality.MODES


def test_old_quality_policy_is_not_silently_reinterpreted(controller, monkeypatch):
    c = controller; inject_findings(monkeypatch, [[finding(status='unknown')]])
    result = c['run']([rust('ownership'), {'action': 'finish'}], mode='rust-only')
    path = c['directory']/'scope-review/review.json'; audit = read(path)
    audit['baseline_quality']['policy'] = 'baseline-quality-separate-from-candidate-scope-v1'
    audit['baseline_quality']['publication_hold'] = True
    save(path, audit)
    result['baseline_quality'] = deepcopy(audit['baseline_quality'])
    result['scope_selection']['review_sha256'] = digest(path)
    sealed = digest(path)
    with pytest.raises(Failure) as error:
        quality.merge_selected(c['original'], {'rust-only': result})
    assert error.value.code == 'optimization_baseline_quality_policy_changed'
    assert digest(path) == sealed


def test_rejected_and_no_gain_review_findings_are_not_lost_by_selection(controller, monkeypatch):
    c = controller; c['review_decisions'].extend(['requires_source_change', 'within_scope', 'within_scope'])
    c['gains'].extend([False, True])
    answers = [[finding()], [finding('not_affected', 'claim_limit')], []]
    inject_findings(monkeypatch, answers)
    result = c['run']([rust('invalid new use'), rust('no gain'), rust('accepted'), {'action': 'finish'}], mode='rust-only')
    assert [r['status'] for r in result['attempts'][:3]] == ['optimization_scope_rejected', 'no_gain', 'accepted']
    assert len(result['baseline_quality']['admission_reports']) == 3
    assert len(result['baseline_quality']['inherited_baseline_findings']) == 2
    assert result['baseline_quality']['publication_hold']
    rejected = result['attempts'][0]['error']['evidence']
    assert digest(rejected['review']) == rejected['review_sha256']
    assert finding('not_affected', 'claim_limit')['finding'] in result['baseline_quality']['claim_limits']


def test_malformed_review_does_not_promote_its_finding_to_valid_baseline_evidence(controller, monkeypatch):
    c = controller; original = opt.Provider
    class Invalid(original):
        def call(self, *args, **kwargs):
            reply = super().call(*args, **kwargs)
            if kwargs.get('phase') == 'performance_scope_admission':
                reply['reviews'][0]['inherited_baseline_findings'] = [finding()]
                reply['reviews'][0]['operation_order_evidence'] = []
            return reply
    monkeypatch.setattr(opt, 'Provider', Invalid)
    result = c['run']([rust('malformed review'), {'action': 'finish'}], mode='rust-only')
    assert result['attempts'][0]['status'] == 'invalid_scope_review'
    assert result['baseline_quality']['inherited_baseline_findings'] == []
    assert not result['baseline_quality']['publication_hold']


def test_claim_limit_is_visible_without_becoming_root_hold(controller, monkeypatch):
    c = controller; inject_findings(monkeypatch, [[finding('not_affected', 'claim_limit')]])
    result = c['run']([rust('ownership'), {'action': 'finish'}], mode='rust-only')
    assert result['attempts'][0]['status'] == 'accepted'
    assert not result['baseline_quality']['publication_hold']
    assert len(result['baseline_quality']['claim_limits']) == 2
    assert 'not a mathematical proof' in result['baseline_quality']['claim_limits'][0]


def test_rejected_admission_tamper_and_baseline_binding_mismatch_fail_closed(controller, monkeypatch, tmp_path):
    c = controller; c['review_decisions'].append('requires_source_change')
    inject_findings(monkeypatch, [[finding()]])
    result = c['run']([rust('bad'), {'action': 'finish'}], mode='rust-only')
    link = result['attempts'][0]['error']['evidence']; path = Path(link['review'])
    audit = read(path); audit['baseline_validation']['baseline_id'] = 'other-baseline'; save(path, audit)
    with pytest.raises(Failure) as exc: quality.collect_admissions(c['original'], result['attempts'])
    assert exc.value.code == 'optimization_admission_changed'
    link['review_sha256'] = digest(path)  # Even a newly sealed record cannot cross the baseline binding.
    with pytest.raises(Failure) as exc: quality.collect_admissions(c['original'], result['attempts'])
    assert exc.value.code == 'optimization_baseline_quality_changed'


def test_matrix_blocks_all_modes_before_build_or_cached_result_and_keeps_manual_review(controller, monkeypatch, tmp_path):
    c = controller; inject_findings(monkeypatch, [[finding()]])
    result = c['run']([rust('accepted'), {'action': 'finish'}], mode='rust-only')
    directory = tmp_path/'matrix'/'example'; directory.mkdir(parents=True)
    save(directory/'result.json', {'status': 'measured', 'sentinel': 'old cached measurement'})
    save(directory.parent/'integrity-review.json', {'status': 'independent', 'publication_hold': True, 'note': 'retain'})
    manual_sha = digest(directory.parent/'integrity-review.json')
    monkeypatch.setattr(matrix, 'selected', lambda *a: (deepcopy(c['original']), deepcopy(result)))
    monkeypatch.setattr(matrix, 'materialize', lambda *a, **k: pytest.fail('Hold must precede every build'))
    held = matrix.measure_case('baseline', 'rust', 'full', {'id': 'example'}, directory)
    assert held['status'] == 'publication_hold' and held['rows'] == []
    assert held['affected_modes'] == ['off', 'rust-only', 'full']
    assert read(directory/'result.json')['sentinel'] == 'old cached measurement'
    assert digest(directory.parent/'integrity-review.json') == manual_sha


def test_either_arm_hold_is_uniform_and_positive_arm_cannot_clear_it(controller, monkeypatch, tmp_path):
    c = controller; inject_findings(monkeypatch, [[finding()], []])
    rust_result = c['run']([rust('R'), {'action': 'finish'}], mode='rust-only')
    full_result = c['run']([{'action': 'finish', 'source_assessment': 'Skip source'}, rust('F'), {'action': 'finish'}],
                           mode='full', destination='full-search')
    merged = quality.merge_selected(c['original'], {'rust-only': rust_result, 'full': full_result})
    assert merged['publication_hold'] and merged['affected_modes'] == quality.MODES
    changed = deepcopy(c['original']); changed['connector'] = {'src/lib.rs': 'different input domain'}
    with pytest.raises(Failure) as exc: quality.merge_selected(changed, {'rust-only': rust_result, 'full': full_result})
    assert exc.value.code == 'optimization_baseline_quality_changed'


def test_matrix_held_case_emits_normal_incomplete_report_without_geomean(monkeypatch, tmp_path):
    base = tmp_path/'base'; rust_run = tmp_path/'rust'; full = tmp_path/'full'
    save(base/'release.json', {'base': 1}); save(rust_run/'optimization-report.json', {'mode': 'rust-only'})
    save(full/'optimization-report.json', {'mode': 'full'})
    monkeypatch.setattr(matrix, 'ROOT', tmp_path/'agent')
    held = {'case': 'example', 'status': 'publication_hold', 'publication_hold': True, 'rows': [],
            'baseline_quality': {'publication_hold': True, 'claim_limits': ['no blanket helper claim']}}
    monkeypatch.setattr(matrix, 'measure_case', lambda *a, **k: deepcopy(held))
    result = matrix.run(base, rust_run, full, [{'id': 'example'}], tmp_path/'matrix')
    assert not result['complete'] and result['status'] == 'publication_hold'
    assert result['primary_geomean_speedups'] == {} and result['held_cases'] == ['example']
    assert read(tmp_path/'matrix/baseline-quality-review.json')['publication_hold']
    assert not (tmp_path/'matrix/integrity-review.json').exists()  # Independent report name is untouched.
    # A later empty/positive report cannot silently clear the existing hold.
    assert matrix.quality_review([], tmp_path/'matrix')['publication_hold']


def test_report_cannot_publish_held_or_detached_quality_even_with_custom_audit(tmp_path):
    script = Path(__file__).parents[1]/'scripts/report_rq2.py'
    spec = importlib.util.spec_from_file_location('_held_rq2_report', script)
    reporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(reporter)
    matrix_dir = tmp_path/'matrix'; matrix_dir.mkdir()
    save(matrix_dir/'baseline-quality-review.json', {'publication_hold': True})
    save(matrix_dir/'matrix.json', {'complete': True, 'publication_hold': False,
        'baseline_quality_review_sha256': digest(matrix_dir/'baseline-quality-review.json')})
    save(tmp_path/'custom.json', {'publication_hold': False})
    with pytest.raises(ValueError, match='uniformly'): reporter.report(matrix_dir, tmp_path/'report', integrity_audit=tmp_path/'custom.json')
    (matrix_dir/'baseline-quality-review.json').unlink()
    with pytest.raises(ValueError, match='missing or changed'): reporter.report(matrix_dir, tmp_path/'report')
