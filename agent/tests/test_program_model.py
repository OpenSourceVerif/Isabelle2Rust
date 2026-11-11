from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from i2r_agent import program_model as pm, task_context as tc
from i2r_agent.common import Failure
from i2r_agent.knowledge import material, requested
from test_task_context import bundle, managed_config


def source_bundle():
    def entity(name, dep=None):
        ty = {'kind': 'free', 'name': "'a", 'sort': ['HOL.type']}
        term = {'kind': 'const', 'name': dep or name, 'type': ty}
        return {'id': 'constant:' + name, 'name': name, 'kind': 'constant',
                'source_type': ty, 'type_variables': [], 'dependencies': ['constant:' + dep] if dep else [],
                'specifications': [], 'function_input_equations': [],
                'execution_equations': [{'arguments': [], 'rhs': {'text': name + ' ORIGINAL', 'term': term}}]}
    b = bundle()
    b['source_model'] = pm.build([{'schema_version': 1, 'entries': ['constant:A.main'],
        'entities': [entity('A.main', 'A.helper'), entity('A.helper', 'A.deep'), entity('A.deep'),
                     {'id': 'class:HOL.type', 'name': 'HOL.type', 'kind': 'class', 'supers': [], 'parameters': []}]}])
    b['original_source_model'] = deepcopy(b['source_model'])
    return b


class ProgramModelTests(unittest.TestCase):
    def test_occurrences_have_instantiated_types_paths_and_reverse_edges(self):
        m = source_bundle()['source_model']
        use = next(u for u in m['uses'] if u['caller'] == 'constant:A.main')
        self.assertEqual(use['path'], 'execution_equations[0].rhs.term')
        self.assertEqual(use['instantiated_type']['sort'], ['HOL.type'])
        self.assertEqual(m['entities']['constant:A.helper']['callers'], ['constant:A.main'])
        self.assertIn('not a dynamic call', use['fact'])

    def test_boundaries_preserve_definition_and_exact_full_closure_read(self):
        b = source_bundle()
        b['base_adapter'] = {'bindings': {'operations': [{'source': 'constant:A.helper'}]}}
        v = pm.view(b)
        ids = {e['id'] for e in v['entities']}
        self.assertIn('constant:A.helper', ids)
        self.assertNotIn('constant:A.deep', ids)
        self.assertIn('A.helper ORIGINAL', json.dumps(v))
        with tempfile.TemporaryDirectory() as d:
            tc.register(b, d)
            r = requested({'request_entities': [{'id': 'constant:A.helper', 'include_dependencies': True,
                                                 'include_callers': True}]}, b)
            self.assertTrue({'constant:A.main', 'constant:A.helper', 'constant:A.deep'} <= {e['id'] for e in r['entities']})
            operation = next(e for e in r['entities'] if e['id'] == 'constant:A.helper')
            self.assertIn('term', operation['execution_equations'][0]['rhs'])

    def test_original_and_current_models_are_not_conflated(self):
        b = source_bundle()
        b['source_model']['entities']['constant:A.main']['execution_equations'][0]['rhs']['text'] = 'ADAPTED'
        with tempfile.TemporaryDirectory() as d:
            tc.register(b, d)
            original = requested({'request_entities': [{'id': 'constant:A.main', 'model_version': 'original'}]}, b)
            current = requested({'request_entities': ['constant:A.main']}, b)
            self.assertIn('A.main ORIGINAL', json.dumps(original))
            self.assertIn('ADAPTED', json.dumps(current))
            self.assertNotEqual(b['model_versions']['original'], b['model_versions']['current'])

    def test_repair_refreshes_semantic_view_without_thingol_body(self):
        b = source_bundle()
        b['programs'][0]['nodes'][0]['statement']['equations'] = ['FORBIDDEN_LEGACY_BODY']
        branch = {'id': 'c1', 'bundle': b, 'files': {'src/lib.rs': 'pub fn f(){}'},
                  'mode': 'generate', 'feedback': {'status': 'compile_failed'}, 'extra': {}}
        with tempfile.TemporaryDirectory() as d:
            result = tc.prepare_generation(branch, {'program': material(b), 'available_actions': []}, managed_config(), d)
            result.pop('_conversation')
            text = json.dumps(result)
            self.assertNotIn('FORBIDDEN_LEGACY_BODY', text)
            self.assertNotIn('thingol', result['program'])
            self.assertIn('A.helper ORIGINAL', text)
            self.assertIn('program_state', result)
            self.assertIn('request_entities', result['available_actions'])
            self.assertTrue(result['base_adapter_version'].startswith('code-'))
            self.assertIn('declarations.thy', result['adapter_files'])
            expanded = requested({'request_graphs': ['G0']}, b)
            self.assertNotIn('FORBIDDEN_LEGACY_BODY', json.dumps(expanded))

    def test_recursive_groups_are_computed_from_source_edges(self):
        self.assertEqual(sorted(pm.components({'a': ['b'], 'b': ['a', 'c'], 'c': []})), [['a', 'b'], ['c']])
        # Large closures must not exhaust Python recursion depth.
        self.assertEqual(len(pm.components({str(i): [str(i+1)] for i in range(1500)})), 1500)

    def test_interface_change_invalidates_behavior_without_promoting_review(self):
        b = source_bundle()
        before = {'src/lib.rs': 'pub fn f(x: u128) -> u128 { x }'}
        after = {'src/lib.rs': 'pub fn f(x: &u128) -> u128 { *x }'}
        branch = {'bundle': b, 'files': after, 'mapping': [{'source': 'constant:A.helper', 'rust_item': 'f'}],
                  'behavior_validated': tc.fingerprint(before),
                  'quality_evidence': {'behavior': {'current': True, 'code_version': tc.fingerprint(before), 'status': 'passed'}}}
        pm.record(branch, {'compilation': {'status': 'passed'}}, before)
        self.assertFalse(branch['quality_evidence']['behavior']['current'])
        self.assertTrue(branch['quality_evidence']['compile']['current'])
        self.assertNotIn('structure_cost', branch['quality_evidence'])
        self.assertIn('constant:A.main', branch['impact']['affected_source_entities'])
        self.assertEqual(branch['impact']['interface_change_candidates'], ['src/lib.rs'])

    def test_unknown_entities_and_conflicting_contexts_are_not_fabricated(self):
        b = source_bundle()
        b['source_model']['entities']['constant:A.main']['dependencies'].append('constant:Unknown.f')
        self.assertIn('constant:Unknown.f', pm.view(b)['unknown_entities'])
        with tempfile.TemporaryDirectory() as d:
            tc.register(b, d)
            with self.assertRaises(Failure):
                requested({'request_entities': ['constant:Unknown.f']}, b)

    def test_connector_change_cannot_reuse_old_behavior_stamp(self):
        branch = {'bundle': source_bundle(), 'files': {'src/lib.rs': 'fn f(){}'}, 'connector': {'src/lib.rs': 'old'}}
        branch['behavior_validated'] = tc.fingerprint(branch['files'])
        pm.record(branch, {'development': {'status': 'passed', 'behavior_checked': True}}, branch['files'])
        self.assertTrue(branch['quality_evidence']['behavior']['current'])
        branch['connector']['src/lib.rs'] = 'changed'
        pm.record(branch, {'compilation': {'status': 'failed'}}, branch['files'])
        self.assertFalse(branch['quality_evidence']['behavior']['current'])

    def test_source_generic_contract_survives_target_removal(self):
        from i2r_agent.export_contract import polymorphic_exports
        b = source_bundle()
        b['programs'] = [{'entries': [], 'nodes': []}]
        self.assertEqual(polymorphic_exports(b)[0]['type_variables'], ["'a"])

    def test_mapping_omission_returns_executable_reply_schema(self):
        from i2r_agent.knowledge import correspondence
        b = bundle()
        with self.assertRaises(Failure) as caught:
            correspondence(b, {'src/lib.rs': 'fn f(){}'}, [])
        evidence = caught.exception.evidence
        self.assertEqual(evidence['repair_protocol']['action'], 'generate')
        self.assertIn('mapping', evidence['repair_protocol'])
        mapping = [{'source': n, 'rust': 'inlined in f'} for n in evidence['missing']]
        self.assertEqual(correspondence(b, {'src/lib.rs': 'fn f(){}'}, mapping)['status'], 'passed')

    def test_optional_null_rust_item_does_not_break_impact_record(self):
        b = source_bundle()
        rows = [{'source': 'constant:A.helper', 'rust': 'crate::f', 'rust_item': None}]
        result = pm.impact(b, {}, {'src/lib.rs': 'fn f(){}'}, rows)
        self.assertIn('constant:A.helper', result['affected_source_entities'])
        self.assertIn('constant:A.main', result['affected_source_entities'])
        from i2r_agent.knowledge import merge_mapping
        self.assertEqual(merge_mapping([], rows), rows)
        for malformed in [False, {'source': 'x'}, [None], [{'source': 'x', 'rust': {}}]]:
            with self.assertRaises(Failure):
                merge_mapping([], malformed)

    def test_relocated_source_is_not_duplicated_but_changed_equation_is(self):
        b = source_bundle()
        entity = b['source_model']['entities']['constant:A.main']
        entity['specifications'] = [{'file': '/original/Algorithm.thy', 'line': 4, 'rules': []}]
        b['original_source_model'] = deepcopy(b['source_model'])
        entity['specifications'][0].update(file='/adapter/Algorithm.thy', line=7)
        self.assertEqual(pm.semantic_changes(b), [])
        entity['execution_equations'][0]['rhs']['text'] = 'CHANGED'
        self.assertEqual(pm.semantic_changes(b), ['constant:A.main'])

    def test_protocol_names_do_not_expand_semantic_focus(self):
        b = source_bundle()
        branch = {'feedback': {'status': 'plan_contract_failed', 'evidence': {'missing': ['constant:A.deep', 'constant:A.helper']}}}
        self.assertEqual(pm.focused_ids(b, branch), {'constant:A.main'})
        branch['feedback']['status'] = 'support_contract_failed'
        self.assertIn('constant:A.helper', pm.focused_ids(b, branch))

    def test_invalid_connector_path_does_not_create_a_quality_issue(self):
        from i2r_agent import repair_state as repair
        branch = {'files': {}, 'mode': 'generate', 'feedback': {'behavior_failure': {'suites': []}}}
        repair.capture(branch)
        identity = branch['repair_issue']['id']
        branch['feedback'] = {'status': 'invalid_candidate_path', 'message': 'connector/src/lib.rs'}
        repair.capture(branch)
        self.assertEqual(branch['repair_issue']['id'], identity)
        self.assertEqual(branch['repair_issue']['kind'], 'behavior')
        self.assertFalse(branch.get('suspended_issues'))
        repair.verified(branch, 'behavior', 'current')
        repair.ensure_acceptible(branch)

    def test_rejected_decision_shape_does_not_break_attempt_record(self):
        branch = {'bundle': source_bundle(), 'files': {'src/lib.rs': 'fn f(){}'},
                  'decisions': [{'id': 'existing', 'choice': 'borrow'}]}
        with self.assertRaises(Failure):
            tc.update_decisions(branch, {'decisions': None})
        with tempfile.TemporaryDirectory() as d:
            tc.record_attempt(branch, {'attempt': 1, 'action_phase': 'generate', 'development': {'status': 'invalid_decisions'}},
                              {}, {'decisions': None}, d)
            self.assertTrue((Path(d)/'repair-event.json').exists())


if __name__ == '__main__':
    unittest.main()
