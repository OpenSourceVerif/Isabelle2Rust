#!/usr/bin/env python3
"""Session-owned coverage for available dependencies with unimported theories."""
import _paths
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import afp_common as common
import scan_frozen as frozen
import scan_store as ss


def entry_fixture():
    # Main imports Core from an available library session, leaving its Docs
    # unloaded. Test inherits Main. Docs must be collected in Lib's own heap.
    info = {'sessions': ['Lib', 'Main', 'Test'],
            'session_requirements': {'Lib': [], 'Main': ['Lib'], 'Test': ['Lib', 'Main']},
            'theories': [{'name': name, 'path': name + '.thy', 'session': name.split('.')[0],
                          'conditions': []}
                         for name in ['Lib.Core', 'Lib.Docs', 'Main.Main', 'Test.Check']]}
    data = {'order': ['E'], 'entries': {'E': info}}
    units = {s: ss.unit_input('E', s, info, {'source': 'fixed'}) for s in info['sessions']}
    loaded = {'Lib': ['Lib.Core', 'Lib.Docs'], 'Main': ['Lib.Core', 'Main.Main'],
              'Test': ['Lib.Core', 'Main.Main', 'Test.Check']}
    return data, units, loaded


def catalogue_xml(unit, loaded):
    ancestors = {'Lib.Core': set(), 'Lib.Docs': {'Lib.Core'},
                 'Main.Main': {'Lib.Core'}, 'Test.Check': {'Lib.Core', 'Main.Main'}}
    root = ET.Element('scan', schema='2', policy=ss.POLICY, method=ss.METHOD, unit=ss.digest(unit))
    for name in unit['requested']:
        ET.SubElement(root, 'requested', name=name)
    for name in loaded:
        ET.SubElement(root, 'loaded', name=name)
        theory = ET.SubElement(root, 'theory', name=name, context=name, declared='1')
        ET.SubElement(theory, 'constant', name=name + '.value', owner=name)
        if not any(name in ancestors.get(other, set()) for other in loaded):
            context = ET.SubElement(root, 'context', name=name)
            for covered in sorted(({name} | ancestors.get(name, set())) & set(loaded)):
                ET.SubElement(context, 'covers', theory=covered)
    return ET.tostring(root, encoding='unicode')


def commit_fixture(store, unit, loaded):
    # Persist real checksummed fixture logs/XML through the production receipt
    # transaction; these stand-ins do not claim that Isabelle was executed.
    attempt = store.next_attempt(unit)
    run = {'unit_id': ss.digest(unit), 'tool_generation': 'fixture', 'runtime': {}}
    common.write_record(attempt / 'attempt.json', run)
    (attempt / 'theories.txt').write_text('\n'.join(unit['requested']) + '\n')
    (attempt / 'catalogue.xml').write_text(catalogue_xml(unit, loaded))
    checks = []
    for name in ['load', 'scan']:
        log = attempt / (name + '.log')
        log.write_text('Synthetic successful command for coverage regression.\n')
        check = {'status': 'passed', 'returncode': 0, 'log': common.relative(log)}
        common.write_record(log.with_suffix('.log.json'), check)
        checks.append(check)
    receipt = ss.completed_receipt(store, attempt, unit, run, *checks)
    store.commit(attempt, receipt)


class SessionCoverageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        context = patch.object(common, 'PROJECT', self.root)
        context.start()
        self.addCleanup(context.stop)
        self.data, self.units, self.loaded = entry_fixture()
        self.store = ss.Store(self.root / 'run')

    def test_available_dependency_need_not_be_fully_loaded(self):
        # The library dependency must remain scheduled even though its Docs
        # theory is not a mandatory member of Main's loaded context.
        unit = self.units['Main']
        self.assertEqual(unit['requirements'], ['Lib'])
        self.assertEqual(unit['expected'], ['Main.Main'])
        commit_fixture(self.store, unit, self.loaded['Main'])
        receipt = ss.Store(self.store.base).read(unit)
        self.assertEqual(receipt['catalogue']['loaded'], self.loaded['Main'])

    def test_missing_owned_theory_is_still_rejected(self):
        # A loaded dependency cannot stand in for the owning session's theory.
        with self.assertRaisesRegex(ValueError, 'required session context'):
            commit_fixture(self.store, self.units['Main'], ['Lib.Core'])

    def test_unrequested_theory_is_still_rejected(self):
        # Relaxing required coverage must not admit foreign theory evidence.
        with self.assertRaisesRegex(ValueError, 'required session context'):
            commit_fixture(self.store, self.units['Main'], self.loaded['Main'] + ['Foreign.X'])

    def test_complementary_sessions_cover_the_complete_entry(self):
        # Docs only occurs in Lib's receipt. Main/Test remain valid and the
        # complete union retains Docs' candidate along with all other theories.
        for session, unit in self.units.items():
            commit_fixture(self.store, unit, self.loaded[session])
        gate = frozen.checkpoint(ss.Store(self.store.base), self.data, self.units, {})
        result, exports = ss.aggregate(self.store, self.data, self.units, {})
        self.assertTrue(gate['passed'], gate)
        self.assertEqual(result['entries']['E']['status'], 'passed')
        self.assertEqual(result['entries']['E']['scan']['missing_theories'], [])
        self.assertEqual(set(exports['E']), {t['path'] for t in self.data['entries']['E']['theories']})
        self.assertEqual(exports['E']['Lib.Docs.thy'], ['Lib.Docs.value'])

    def test_union_coverage_does_not_replace_a_required_session_receipt(self):
        # Even if Main loads every library theory, a missing Lib receipt must
        # keep the entry and scan gate incomplete rather than borrowing coverage.
        commit_fixture(self.store, self.units['Main'], self.loaded['Main'] + ['Lib.Docs'])
        commit_fixture(self.store, self.units['Test'], self.loaded['Test'])
        gate = frozen.checkpoint(self.store, self.data, self.units, {})
        result, _ = ss.aggregate(self.store, self.data, self.units, {})
        self.assertFalse(gate['passed'])
        self.assertEqual(result['entries']['E']['status'], 'pending')
        self.assertEqual(result['entries']['E']['scan']['missing_theories'], [])

    def test_complete_receipts_cannot_hide_an_entry_manifest_gap(self):
        # Mismatched/truncated unit inputs may all pass locally. An additional
        # manifest theory must nevertheless fail aggregation and the scan gate.
        for session, unit in self.units.items():
            commit_fixture(self.store, unit, self.loaded[session])
        missing = {'name': 'Extra.Omitted', 'path': 'Extra.Omitted.thy', 'session': 'Extra'}
        self.data = copy.deepcopy(self.data)
        self.data['entries']['E']['theories'].append(missing)
        gate = frozen.checkpoint(self.store, self.data, self.units, {})
        result, _ = ss.aggregate(self.store, self.data, self.units, {})
        self.assertEqual(result['entries']['E']['status'], 'failed')
        self.assertFalse(gate['passed'])
        self.assertIn({'entry': 'E', 'status': 'incomplete_theory_coverage',
                       'missing_theories': [missing]}, gate['issues'])

    def test_retained_units_keep_their_committed_coverage_requirement(self):
        # New units have a different identity where the required set changes.
        # A frozen unit must still enforce its original, stronger requirement.
        old = copy.deepcopy(self.units['Main'])
        old['expected'] = ['Lib.Core', 'Lib.Docs', 'Main.Main']
        self.assertNotEqual(ss.digest(old), ss.digest(self.units['Main']))
        with self.assertRaisesRegex(ValueError, 'required session context'):
            commit_fixture(self.store, old, self.loaded['Main'])


@unittest.skipUnless(os.environ.get('AFP_TEST_AUTOCORRES_COVERAGE') == '1',
                     'opt-in current-run AutoCorres2 catalogue regression')
class AutoCorresCatalogueTests(unittest.TestCase):
    def test_original_catalogues_satisfy_owned_and_union_coverage(self):
        # Read and verify retained evidence, then rebind only the unit ID in a
        # temporary XML fixture to exercise the new rule. No historical receipt
        # is upgraded, and the temporary fixture is not a native execution fact.
        from state import State
        base = common.WORK
        run = State(base).get('run')
        self.assertIsNotNone(run, 'Run a current scan before enabling the native coverage check')
        data = run['manifest']
        units = frozen.make_units(data, run['sources'])
        info = data['entries']['AutoCorres2']
        store = ss.Store(base)
        covered = set()
        for session, count in [('AutoCorres2', 128), ('AutoCorres2_Main', 2), ('AutoCorres2_Test', 264)]:
            old = units[session]
            receipt = store.read(old)
            xml_name, = [p for p in receipt['evidence'] if p.endswith('/catalogue.xml')]
            original = store.path(xml_name)
            unit = ss.unit_input('AutoCorres2', session, info, old['source'])
            self.assertEqual(len(unit['expected']), count)
            xml = ET.parse(original).getroot()
            xml.set('unit', ss.digest(unit))
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'catalogue.xml'
                ET.ElementTree(xml).write(path, encoding='utf-8')
                catalogue = ss.parse_catalogue(path, unit)
            covered.update(catalogue['scope'])
            self.assertEqual(ss.file_digest(original), receipt['evidence'][xml_name]['sha256'])
        self.assertEqual(covered, {t['path'] for t in info['theories']})
        self.assertEqual(len(covered), 394)


if __name__ == '__main__':
    unittest.main()
