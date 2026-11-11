import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent.common import Failure, config
from i2r_agent import task_context as tc, repair_state
from i2r_agent.repair_actions import EditController
from i2r_agent.test_connector import connect
from i2r_agent.source_run import search
from i2r_agent.knowledge import merge_mapping
from i2r_agent.source_context import coverage
from test_source_workflow import bundle, mapping


FIXTURE = json.loads((Path(__file__).parent / 'fixtures/ackermann-connector-repair.json').read_text())


class RepairActionTests(unittest.TestCase):
    def test_mapping_removal_is_explicit_and_required_coverage_cannot_be_deleted(self):
        previous=mapping()+[{'source':'constant:Cmp.cmp_val','rust':'CmpVal'}]
        self.assertEqual(merge_mapping(previous,mapping()),previous)
        fixed=merge_mapping(previous,None,['constant:Cmp.cmp_val'])
        files={'src/lib.rs':'pub fn f()->u128 { 1 }'}
        self.assertEqual(coverage(bundle(),files,fixed)['status'],'passed')
        with self.assertRaises(Failure):coverage(bundle(),files,merge_mapping(fixed,None,['constant:A.f']))
        with self.assertRaises(Failure):merge_mapping(previous,None,['missing'])
        with self.assertRaises(Failure):merge_mapping(previous,[previous[-1]],['constant:Cmp.cmp_val'])
        self.assertEqual(len(previous),2)

    def test_contract_failure_survives_action_rejection_and_closes_after_recheck(self):
        cfg=config();cfg['generation']['workflow']='source-v6'
        provider=Mock();provider.phase_calls={'generation':0};provider.calls=0;provider.usage={}
        requests=[]
        def ask(provider,cfg,path,stage,p):
            requests.append(p);provider.calls+=1;provider.phase_calls['generation']+=1
            phase=p['controller_state']['phase']
            if phase=='generate':return {'files':{'src/lib.rs':'pub fn f()->u128 { 1 }'},
                'mapping':mapping()+[{'source':'constant:Cmp.cmp_val','rust':'CmpVal'}]}
            if phase in {'quick_refine','review'}:return {'action':'accept','quality_review':'No changes'}
            if sum(r['controller_state']['phase']=='repair' for r in requests)==1:
                return {'mapping':mapping()} # Old proposal only omits the erroneous record.
            self.assertEqual(p['original_issue']['kind'],'contract')
            self.assertIn('constant:Cmp.cmp_val',str(p['original_issue']['evidence']))
            return {'remove_mapping':['constant:Cmp.cmp_val']}
        with tempfile.TemporaryDirectory() as d,patch('i2r_agent.source_run.call',side_effect=ask),\
             patch('i2r_agent.source_run.compile_library',return_value={'status':'passed','checks':{},'diagnostics':[]}):
            attempts,survivors=search(bundle(),None,cfg,provider,Path(d),Mock(),{},[],[],Path(d)/'r.json',lambda _:None)
            self.assertEqual(len(survivors),1)
            removed=next(a for a in attempts if a['repair_event']['mapping_changes']['removed'])
            self.assertEqual(removed['repair_event']['mapping_changes']['removed'],['constant:Cmp.cmp_val'])
            self.assertFalse(removed['repair_event']['edit_execution']['code_changed'])
            self.assertTrue(removed['repair_event']['edit_execution']['metadata_changed'])
            self.assertEqual(survivors[0]['closed_issues'][-1]['kind'],'contract')

    def test_original_rejected_model_patch_applies_through_real_connector(self):
        data = FIXTURE['input']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, content in data['scenario_sources'].items():(root / name).write_text(content)
            provider = Mock();provider.call.return_value = deepcopy(FIXTURE['reply'])
            previous = deepcopy(data['previous_connector'])
            cfg=config();cfg['testing']['transport']='dashu-ubig'
            result, _ = connect(root, root, data['algorithm_files'], data['mapping'],
                {'dependencies': data['algorithm_dependencies']}, cfg, provider, root / 'attempt',
                previous, data['feedback'], context_directory=root / 'context', original_issue=data['feedback'])
            self.assertEqual(provider.call.call_count, 1)
            self.assertIn('n = Nat::suc(n);', result['src/lib.rs'])
            self.assertEqual(previous, data['previous_connector'])
            self.assertEqual(json.loads((root / 'attempt/reply.json').read_text()), FIXTURE['reply'])
            operation = json.loads((root / 'attempt/edit-operation.json').read_text())
            self.assertTrue(operation['applied'])
            self.assertEqual(operation['validation'], 'not_run')
            self.assertEqual(operation['changed_files'], ['connector/src/lib.rs'])

    def test_read_file_id_is_directly_editable_without_version_echo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ['Model.thy', 'Kernel.thy']:(root / name).write_text('source')
            provider = Mock()
            provider.call.side_effect = [
                {'request_files': [{'path': 'connector/src/lib.rs'}]},
                {'edits': [{'file': 'connector/src/lib.rs', 'old': 'bad', 'new': 'good'}]}]
            cfg=config();cfg['testing']['transport']='native-u128'
            result, _ = connect(root, root, {}, [], {'dependencies': {}}, cfg, provider, root / 'attempt',
                {'src/lib.rs': 'bad'}, {'status': 'compile_failed'}, context_directory=root / 'context')
            request = json.loads(provider.call.call_args.args[1])
            self.assertEqual(request['requested_material']['files'][0]['path'], 'connector/src/lib.rs')
            self.assertEqual(request['previous_connector'], {'connector/src/lib.rs': 'bad'})
            self.assertEqual(result, {'src/lib.rs': 'good'})

    def test_implicit_snapshot_checks_full_replacements_and_explicit_stale_versions(self):
        with tempfile.TemporaryDirectory() as d:
            ctl = EditController(Path(d) / 'context', 'algorithm')
            snapshot = {'src/lib.rs': 'old'}
            current = {'src/lib.rs': 'concurrent change'}
            with self.assertRaises(Failure) as e:
                ctl.apply(current, {'files': {'src/lib.rs': 'replacement'}}, snapshot, Path(d) / '1')
            self.assertEqual(e.exception.code, 'stale_patch')
            with self.assertRaises(Failure) as e:
                ctl.apply(snapshot, {'base_code_version': 'obsolete', 'files': {'src/lib.rs': 'replacement'}}, snapshot, Path(d) / '2')
            self.assertEqual(e.exception.code, 'stale_patch')
            self.assertEqual(current['src/lib.rs'], 'concurrent change')

    def test_rejected_multi_file_patch_is_atomic_and_errors_are_specific(self):
        with tempfile.TemporaryDirectory() as d:
            ctl = EditController(Path(d) / 'context', 'algorithm')
            files = {'src/lib.rs': 'one two', 'src/helper.rs': 'other'}
            reply = {'edits': [{'file': 'src/lib.rs', 'old': 'one', 'new': 'ONE'},
                               {'file': 'src/helper.rs', 'old': 'absent', 'new': 'X'}]}
            with self.assertRaises(Failure) as e:ctl.apply(files, reply, deepcopy(files), Path(d) / '1')
            self.assertEqual(e.exception.code, 'edit_text_mismatch')
            self.assertEqual(e.exception.evidence['matches'], 0)
            self.assertEqual(files['src/lib.rs'], 'one two')
            self.assertEqual(ctl.events[-1]['changed_files'], [])
            reply['edits'][1]['file'] = 'src/missing.rs'
            with self.assertRaises(Failure) as e:ctl.apply(files, reply, files, Path(d) / '2')
            self.assertEqual(e.exception.code, 'unknown_edit_file')
            self.assertIn('src/helper.rs', e.exception.evidence['editable_files'])

    def test_connector_cannot_edit_algorithm_with_patch_or_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            ctl = EditController(Path(d) / 'context', 'connector');files = {'src/lib.rs': 'old'}
            for i, reply in enumerate([
                    {'edits': [{'file': 'algorithm/src/lib.rs', 'old': 'old', 'new': 'new'}]},
                    {'files': {'algorithm/src/lib.rs': 'new'}}]):
                with self.assertRaises(Failure) as e:ctl.apply(files, reply, files, Path(d) / str(i))
                self.assertEqual(e.exception.code, 'read_only_edit')
            self.assertEqual(files, {'src/lib.rs': 'old'})

    def test_alternating_errors_survive_resume_and_trigger_recovery_then_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);files = {'src/lib.rs': 'old'}
            rejected = [
                {'base_code_version': 'stale', 'edits': [{'file': 'src/lib.rs', 'old': 'old', 'new': 'new'}]},
                {'edits': [{'file': 'src/wrong.rs', 'old': 'old', 'new': 'new'}]}]
            for i in range(4):
                ctl = EditController(root / 'context', 'connector')
                with self.assertRaises(Failure) as e:ctl.apply(files, rejected[i % 2], files, root / str(i))
                if i == 1:
                    state = ctl.context(files)
                    self.assertEqual(state['recovery'], 'replace_files')
                    self.assertEqual({e['status'] for e in state['unresolved_action_errors']}, {'stale_patch', 'unknown_edit_file'})
                    self.assertEqual(state['recent_patch_proposals'][0]['reply'], rejected[0])
                if i == 3:self.assertEqual(e.exception.code, 'repair_protocol_stalled')
            self.assertEqual(files, {'src/lib.rs': 'old'})

    def test_full_file_recovery_resets_stall_and_checks_remain_separate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);ctl = EditController(root / 'context', 'algorithm');files = {'src/lib.rs': 'old'}
            for i in range(2):
                with self.assertRaises(Failure):ctl.apply(files, {'edits': [{'file': 'src/lib.rs', 'old': 'missing', 'new': 'new'}]}, files, root / str(i))
            result = ctl.apply(files, {'files': {'src/lib.rs': 'new'}}, files, root / 'recovered')
            self.assertEqual(ctl.context(result)['consecutive_unapplied_actions'], 0)
            ctl.verify(result, 'compile', 'passed', root / 'compile.json')
            ctl.verify(result, 'behavior', 'mismatch', root / 'test.json')
            event = EditController(root / 'context', 'algorithm').events[-1]
            self.assertEqual([c['status'] for c in event['checks']], ['passed', 'mismatch'])
            branch = {'files': files, 'feedback': {'status': 'compile_failed'}}
            repair_state.capture(branch);identity = branch['repair_issue']['id']
            branch['feedback'] = {'status': 'repair_protocol_stalled'};repair_state.capture(branch)
            self.assertEqual(branch['repair_issue']['id'], identity)

    def test_algorithm_loop_stops_unapplied_actions_without_spending_fifty_calls(self):
        cfg = config();cfg['generation']['workflow'] = 'source-v6'
        provider = Mock();provider.phase_calls = {'generation': 0};provider.calls = 0;provider.usage = {}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);out = root / 'out';out.write_text('');err = root / 'err';err.write_text('wrong type')
            requests = []
            def ask(provider, cfg, path, stage, p):
                provider.phase_calls['generation'] += 1;provider.calls += 1;requests.append(p)
                if p['controller_state']['phase'] == 'generate':
                    return {'files': {'src/lib.rs': 'pub fn f()->u128 { false }'}, 'mapping': mapping()}
                if p['controller_state']['phase'] == 'quick_refine':return {'action': 'accept', 'quality_review': 'No changes'}
                return {'edits': [{'file': 'src/no_file.rs', 'old': 'false', 'new': '1'}]}
            failed = {'status': 'compile_failed', 'checks': {'build': {'stdout': str(out), 'stderr': str(err)}}, 'diagnostics': []}
            with patch('i2r_agent.source_run.call', side_effect=ask), patch('i2r_agent.source_run.compile_library', return_value=failed):
                attempts, survivors = search(bundle(), None, cfg, provider, root, Mock(), {}, [], [], root / 'r.json', lambda _: None)
            self.assertFalse(survivors)
            self.assertEqual(attempts[-1]['development']['status'], 'repair_protocol_stalled')
            self.assertEqual(provider.calls, 6)
            self.assertEqual(requests[-1]['repair_execution']['recovery'], 'replace_files')
            self.assertEqual(requests[-1]['original_issue']['kind'], 'compile')

    def test_connector_loop_uses_execution_context_and_records_actual_diff(self):
        for recover in [True, False]:
            with self.subTest(recover=recover), tempfile.TemporaryDirectory() as d:
                root=Path(d);cfg=config();cfg['generation']['workflow']='source-v6'
                cfg['testing']['transport']='native-u128'
                for name in ['Model.thy','Kernel.thy']:(root/name).write_text('source')
                out=root/'out';out.write_text('');err=root/'err';err.write_text('missing function bad')
                provider=Mock();provider.phase_calls={'generation':0};provider.calls=0;provider.usage={}
                requests=[]
                def count():
                    provider.calls+=1;provider.phase_calls['generation']+=1
                def algorithm(*args):
                    count();p=args[-1]
                    if p['controller_state']['phase']=='generate':
                        return {'files':{'src/lib.rs':'pub fn f()->u128 { 1 }'},'mapping':mapping()}
                    return {'action':'accept','quality_review':'No changes'}
                def connector(system,prompt,**kwargs):
                    count();p=json.loads(prompt);requests.append(p)
                    if len(requests)==1:return {'files':{'connector/src/lib.rs':'fn observe(){ bad(); }'}}
                    if recover and len(requests)>=4:
                        return {'files':{'connector/src/lib.rs':'fn observe(){ good(); }'}}
                    return {'edits':[{'file':'connector/src/missing.rs' if len(requests)%2 else 'connector/src/lib.rs',
                                     'old':'absent','new':'good'}]}
                provider.call.side_effect=connector
                def compile_connector(crate,*args,**kwargs):
                    if 'bad()' in (crate/'src/lib.rs').read_text():
                        return {'status':'compile_failed','checks':{'build':{'stdout':str(out),'stderr':str(err)}}}
                    return {'status':'passed','checks':{},'binary':'mock-binary'}
                b=bundle();b['case']='fixture'
                suite={'status':'passed','count':1,'failures':0,'counterexamples':[]}
                with patch('i2r_agent.source_run.call',side_effect=algorithm),\
                     patch('i2r_agent.source_run.compile_library',return_value={'status':'passed','checks':{},'diagnostics':[]}),\
                     patch('i2r_agent.source_run.compile_rust',side_effect=compile_connector),\
                     patch('i2r_agent.source_run.check_suite',return_value=suite):
                    attempts,survivors=search(b,root,cfg,provider,root,Mock(),{},[[0]],[],root/'r.json',lambda _:None)
                self.assertEqual(requests[-1]['repair_execution']['recovery'],'replace_files')
                self.assertEqual(requests[-1]['original_issue']['status'],'compile_failed')
                self.assertEqual(len(requests[-1]['repair_execution']['unresolved_action_errors']),2)
                if recover:
                    self.assertEqual(len(survivors),1)
                    repaired=next(a for a in attempts if a.get('repair_event',{}).get('edit_execution',{}).get('outcome')=='applied'
                                  and a['repair_event']['edit_execution']['before_version']!='code-'+tc.fingerprint({}))
                    self.assertEqual(repaired['repair_event']['changed_connector_files'],['src/lib.rs'])
                    self.assertNotEqual(repaired['repair_event']['connector_before'],repaired['repair_event']['connector_after'])
                    self.assertTrue(survivors[0]['closed_issues'])
                else:
                    self.assertFalse(survivors)
                    self.assertEqual(attempts[-1]['development']['status'],'repair_protocol_stalled')
                    self.assertEqual(len(requests),5)


if __name__ == '__main__':unittest.main()
