"""Read-only controller audit: fake model replies, real Rust compilation, no API calls."""
import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock, patch

from i2r_agent import segmented_v8 as runner, semantic_components as components
from i2r_agent import knowledge_run
from i2r_agent.common import Failure, Executor, save, read
from test_segmented_workflow import source, mapping
from test_v8_workflow import cfg, accept
from test_semantic_components import group

import tempfile
import unittest
TEMP = tempfile.TemporaryDirectory()
ROOT = Path(TEMP.name)


def provider():
    p = Mock()
    p.calls = 0
    p.phase_calls = {'generation': 0, 'preprocessing': 0}
    p.usage = {}
    return p


def run_fixture(name, bundle, conf, reply):
    work = ROOT / (name + '-' + str(len(list(ROOT.glob(name + '-*'))) + 1))
    work.mkdir()
    save(work / 'regressions.json', [])
    failure = None
    with patch('i2r_agent.segmented_v8.ask', side_effect=reply):
        try:
            runner.search(bundle, None, conf, provider(), work, Executor(work / 'commands'),
                          None, [], [], work / 'regressions.json', lambda _: None)
        except Failure as e:
            failure = {'code': e.code, 'message': str(e), 'evidence': e.evidence}
    state = read(work / 'segmented-checkpoint.json')
    return failure, state


def incomplete_first_review():
    conf = cfg()
    conf['segmented']['support_tests'] = False
    conf['v8']['unit_policy'] = 'semantic-components'
    b = source()
    b['workflow'] = 'segmented-v8'
    b['segmentation'] = components.compose(b['source_model'], [],
        [group('pair', 'constant:A.h', 'constant:A.f')])
    reviewed = []

    def reply(pv, c, path, p, analysis=False):
        phase = p['controller_state']['phase']
        if phase == 'generate':
            return {'files': {'src/lib.rs': 'pub fn h()->u128{1}\npub fn f()->u128{h()+1}\n'},
                    'mapping': [mapping('h'), mapping('f')],
                    'strategy_version': p['controller_state']['strategy_version'],
                    'strategy_updates': [{'id': 'f-interface', 'expected_revision': 0,
                        'kind': 'interface', 'sources': ['constant:A.f'], 'choice': 'return u128',
                        'conditions': [], 'reason': 'record implemented interface',
                        'status': 'adopted', 'links': ['mapping']}]}
        if phase == 'refine':
            reviewed.append(p['review_scope']['members_to_review'])
        if phase == 'repair':
            raise Failure('needs_user', 'Audit stops here after reproducing missing member evidence')
        return accept(p, conf)

    failure, state = run_fixture('first-review', b, conf, reply)
    compiled = next(a for a in state['attempts'] if a['action_phase'] == 'compile')
    assert reviewed == [['constant:A.f','constant:A.h']], reviewed
    assert compiled['compilation']['status'] == 'passed'
    assert state['status'] == 'passed', state['status']
    return {'first_review_members': reviewed, 'compilation': 'passed',
            'controller_status': state['status']}


def rollback_review_conflict():
    conf = cfg()
    conf['segmented']['support_tests'] = False
    b = source()
    b['workflow'] = 'segmented-v8'
    target = None
    whole_count = 0

    def reply(pv, c, path, p, analysis=False):
        nonlocal target, whole_count
        phase = p['controller_state']['phase']
        if phase == 'generate':
            n = p['unit']['members'][0].rsplit('.', 1)[-1]
            return {'files': {'src/lib.rs': p['current_files']['src/lib.rs'] +
                    '\npub fn ' + n + '()->u128{' + ('1' if n == 'h' else 'h()+1') + '}'},
                    'mapping': [mapping(n)]}
        if phase == 'whole_review':
            whole_count += 1
            if whole_count == 1:
                target = p['controller_state']['state_version']
                return {'edits': [{'file': 'src/lib.rs', 'old': 'h()+1', 'new': '1+h()'}]}
            if whole_count == 2:
                return {'action': 'rollback', 'transaction_before': target}
        return accept(p, conf)

    failure, state = run_fixture('rollback', b, conf, reply)
    assert failure is None, failure
    assert state['status']=='passed',state['status']
    assert b['segmentation']['owner']['constant:A.f'] in state['completed']
    assert any(a.get('development', {}).get('status') == 'transaction_rolled_back' for a in state['attempts'])
    assert state['review_work']
    assert state['files']['src/lib.rs'].endswith('h()+1}')
    return {'error': failure, 'valid_code_restored': True,
            'completed_units': state['completed'], 'review_guard_entries': len(state['review_work'])}


def stale_preprocessing():
    work = ROOT / ('preprocessing-' + str(len(list(ROOT.glob('preprocessing-*'))) + 1))
    work.mkdir()
    project = work / 'project'
    project.mkdir()
    (project / 'Export.thy').write_text('theory Export imports Main begin definition f where "f = (2::nat)" end')
    b = source()
    b.update(workflow='segmented-v8', tool_sources={},
             sources={'Export.thy': 'theory Export imports Main begin definition f where "f = (1::nat)" end'})
    save(work / 'prepared-program.json', b)
    captured = {}

    def search(bundle, *args, **kwargs):
        captured.update(deepcopy(bundle))
        raise Failure('audit_capture', 'Reached generation with cached source')

    with patch('i2r_agent.knowledge_run.Provider', return_value=provider()), \
         patch('i2r_agent.knowledge_run.preprocess') as preprocess, \
         patch('i2r_agent.knowledge_run.analyze') as analyze, \
         patch('i2r_agent.segmented_v8.search', side_effect=search):
        result = knowledge_run.build(project, work / 'output', cfg(), diagnostics=work)
    assert result['status'] == 'stale_preprocessing_cache', result
    assert not preprocess.called and not analyze.called
    assert not captured
    return {'preprocess_calls': preprocess.call_count, 'analysis_calls': analyze.call_count,
            'stale_source_reached_generation': bool(captured), 'result_status': result['status']}


def disabled_required_test():
    from i2r_agent.v8_support import validate_obligations
    from i2r_agent.segmented_support import execute
    from i2r_agent.segmented_config import materialize, rust_config
    conf = cfg()
    rc = rust_config({}, conf)
    work = ROOT / ('disabled-test-' + str(len(list(ROOT.glob('disabled-test-*'))) + 1))
    code = '''#[test] #[cfg(any())]
fn mandatory_boundary() { assert_eq!(i2r_candidate::f(), 0); }
#[test]
fn ordinary_case() { assert_eq!(i2r_candidate::f(), 2); }
'''
    required = [{'source': 'constant:A.f', 'category': 'public_behavior'}]
    obligations = [{'source': 'constant:A.f', 'category': 'public_behavior',
                    'test_name': 'mandatory_boundary', 'case': 'required boundary',
                    'expected_basis': 'audit synthetic expectation'}]
    validate_obligations({'test_source': code, 'obligations': obligations}, required)
    crate = materialize(work / 'crate', {'src/lib.rs': 'pub fn f()->u128{2}'}, rc)
    frozen = {'identity': 'audit-disabled', 'tests': [code], 'unit_tests': [], 'obligations': obligations}
    result = execute(frozen, crate, rc, conf, Executor(work / 'commands'))
    assert result['status'] == 'support_coverage_missing', result
    assert result['missing_required_tests']==['mandatory_boundary']
    assert result['tests_passed'] == 1
    assert 'mandatory_boundary' not in result['diagnostic']
    enabled = {**frozen, 'tests': [code.replace('#[cfg(any())]', '')]}
    control = execute(enabled, crate, rc, conf, Executor(work / 'control-commands'))
    assert control['status'] == 'support_contract_failed'
    save(work / 'results.json', {'disabled': result, 'enabled_control': control})
    return {'obligation_validator': 'accepted', 'disabled_test_result': result['status'],
            'actually_passed_tests': result['tests_passed'],
            'required_test_executed': False, 'same_test_enabled_result': control['status']}



class CorrectnessRepairs(unittest.TestCase):
    def test_first_review_includes_unreviewed_members(self):incomplete_first_review()
    def test_rollback_restores_bound_evidence(self):rollback_review_conflict()
    def test_legacy_cache_never_reaches_generation(self):stale_preprocessing()
    def test_disabled_required_test_is_not_coverage(self):disabled_required_test()
    def test_correctness_mode_overrides_legacy_performance_settings(self):
        from i2r_agent.segmented_config import configure
        c=cfg();c['v8']['correctness_only']=True;c['budgets']['max_model_calls']=60
        c=configure(c)
        self.assertFalse(c['performance']['enabled'])
        self.assertFalse(c['segmented']['development_performance'])
        self.assertFalse(c['v8']['performance_refinement'])
        self.assertNotIn('cost',c['segmented']['review_categories'])
        self.assertEqual(c['testing']['final_cases'],0)
    def test_duplicate_test_names_do_not_mask_disabled_test(self):
        from i2r_agent.segmented_support import required_test_bindings
        f={'tests':['#[test] #[cfg(any())] fn edge(){} mod nested { #[test] fn edge(){} }'],
           'obligations':[{'test_name':'edge'}]}
        self.assertEqual(len(required_test_bindings(f)['edge']),2)
        f['obligations']=[{'test_name':'nested::edge'}]
        self.assertEqual(required_test_bindings(f)['nested::edge'],['__i2r_source_contract_0::nested::edge'])

    def test_fpp_suites_respect_declared_observation_domains(self):
        from i2r_agent import fpp_suites
        for case in fpp_suites.KINDS:
            for x in fpp_suites.fixed(case)+fpp_suites.generate(case,40,123):
                self.assertTrue(fpp_suites.domain(case,x),(case,x))

    def test_cache_identity_tracks_source_and_configuration(self):
        from i2r_agent import prepared_identity
        from i2r_agent.common import save
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'Export.thy').write_text('theory Export imports Main begin end')
            c=cfg();a=prepared_identity.identity(p,c)
            self.assertEqual(a,prepared_identity.identity(p,c))
            (p/'Export.thy').write_text('theory Export imports Main begin definition x where "x=True" end')
            self.assertNotEqual(a,prepared_identity.identity(p,c))
            (p/'Export.thy').write_text('theory Export imports Main begin end')
            self.assertEqual(a,prepared_identity.identity(p,c))
            c['testing']['seed']+=1
            self.assertNotEqual(a,prepared_identity.identity(p,c))

    def _cached_build(self, change):
        from i2r_agent import prepared_identity,tool_sources,task_context
        from i2r_agent.common import digest
        with tempfile.TemporaryDirectory() as d:
            work=Path(d);project=work/'project';project.mkdir()
            source_file=project/'Export.thy';source_file.write_text('theory Export imports Main begin end')
            imported=work/'Imported.thy';imported.write_text('theory Imported imports Main begin end')
            c=cfg();b=source()
            b.update(workflow='segmented-v8',tool_sources=tool_sources.manifest(),sources={'Export.thy':source_file.read_text()},
                     source_catalog=[{'path':str(imported),'available':True,'sha256':digest(imported)}])
            b['prepared_identity']=prepared_identity.identity(project,c)
            old_identity=b['prepared_identity']
            if change in {'source','checkpoint'}:source_file.write_text('theory Export imports Main begin definition f where "f=True" end')
            if change=='imported':imported.write_text('theory Imported imports Main begin definition f where "f=True" end')
            if change=='checkpoint':
                checkpoint_identity=task_context.fingerprint({'workflow_schema':'compile-integration-v2','connector_scenarios':{},'source':b['source_model'],'config':c,'analysis':b['semantic_analysis'],'prepared_identity':old_identity})
                save(work/'segmented-checkpoint.json',{'identity':checkpoint_identity,'implementation_strategy':{'schema':1,'revision':0,'decisions':[],'history':[]}})
                b['sources']['Export.thy']=source_file.read_text()
                b['prepared_identity']=prepared_identity.identity(project,c)
            save(work/'prepared-program.json',b)
            with patch('i2r_agent.knowledge_run.Provider',return_value=provider()), \
                 patch('i2r_agent.knowledge_run.preprocess') as preprocess, \
                 patch('i2r_agent.knowledge_run.analyze') as analyze, \
                 patch('i2r_agent.segmented_v8.ask',side_effect=AssertionError('No model call allowed')):
                if change=='valid':
                    with patch('i2r_agent.segmented_v8.search',side_effect=Failure('audit_capture','Valid current cache reached generation')) as search:
                        result=knowledge_run.build(project,work/'output',c,diagnostics=work)
                        self.assertEqual(search.call_count,1)
                else:
                    result=knowledge_run.build(project,work/'output',c,diagnostics=work)
            self.assertFalse(preprocess.called)
            self.assertFalse(analyze.called)
            return result

    def test_valid_current_prepared_identity_reaches_generation(self):
        self.assertEqual(self._cached_build('valid')['status'],'audit_capture')

    def test_current_prepared_cache_rejects_changed_local_source_before_generation(self):
        self.assertEqual(self._cached_build('source')['status'],'stale_preprocessing_cache')

    def test_current_prepared_cache_rejects_changed_imported_catalog_source(self):
        self.assertEqual(self._cached_build('imported')['status'],'stale_preprocessing_cache')

    def test_new_prepared_identity_rejects_old_checkpoint_with_same_graph(self):
        self.assertEqual(self._cached_build('checkpoint')['status'],'stale_snapshot')
