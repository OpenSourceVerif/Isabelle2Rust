import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from i2r_agent.common import Failure
from test_translation_workflow import cfg as config
from i2r_agent import task_context as tc, repair_state
from i2r_agent.repair_actions import EditController
from i2r_agent.test_connector import connect
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


if __name__ == '__main__':unittest.main()
