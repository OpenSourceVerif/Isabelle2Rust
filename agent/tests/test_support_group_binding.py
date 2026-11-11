import tempfile,unittest,json
from pathlib import Path
from i2r_agent import segmented_support as support,v8_repair as repair
from i2r_agent.common import Failure
from i2r_agent.task_context import Archive,fingerprint

class GroupBindingTests(unittest.TestCase):
    def test_cross_group_short_names_bind_independently(self):
        code='#[test] fn edge() {}'
        a=support.group_obligations([code],[],[{'test_name':'edge','expected_basis':'source A'}])
        b=support.group_obligations([code],[],[{'test_name':'edge','expected_basis':'source B'}],1)
        f={'tests':[code,code],'obligations':a+b}
        bindings=support.required_test_bindings(f)
        self.assertEqual(list(bindings),['__i2r_source_contract_0::edge','__i2r_source_contract_1::edge'])
        # A successful sibling cannot satisfy an ignored/cfg-disabled owning group.
        executed={'__i2r_source_contract_1::edge'}
        for attribute in ['#[ignore]','#[cfg(any())]']:
            f['tests'][0]=attribute+code
            missing=[name for name,rows in support.required_test_bindings(f).items() if len(rows)!=1 or rows[0] not in executed]
            self.assertEqual(missing,['__i2r_source_contract_0::edge'])
    def test_local_ambiguity_and_stale_qualified_name_fail_closed(self):
        for code,name,offset in [('#[test] fn edge() {} mod nested { #[test] fn edge() {} }','edge',0),
                                 ('#[test] fn edge() {}','__i2r_source_contract_0::edge',1)]:
            with self.assertRaises(Failure):support.group_obligations([code],[],[{'test_name':name}],offset)
    def test_unit_offsets_and_nested_module_are_bound(self):
        rows=support.group_obligations([], [{'source':'#[test] fn edge() {}','file':'src/lib.rs','module':['private']}],[{'test_name':'edge'}],0,2)
        self.assertEqual(rows[0]['test_name'],'private::__i2r_contract_2::edge')
    def test_evidence_dedup_exact_bounded_read_and_reject_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            bundle={'_context_archive':d};cfg={'segmented':{'initial_source_characters':4000}}
            value=['immutable expected=42\n'*700]
            result={'status':'support_coverage_missing','missing_required_tests':['edge'],'immutable_test_sources':value}
            payload=repair.bounded_evidence({'feedback':result,'open_failures':[],'repair_issue':{'original':result,'latest':result}},bundle,cfg)
            self.assertEqual(payload['feedback']['status'],'support_coverage_missing')
            self.assertEqual(payload['feedback']['missing_required_tests'],['edge'])
            refs=payload['feedback']['immutable_test_sources']['pages']
            self.assertEqual(len(payload['repair_evidence_catalog']),len(refs))
            rows=repair.read_evidence(refs,payload['repair_evidence_catalog'],bundle,cfg)
            self.assertLessEqual(sum(len(r['text']) for r in rows['evidence_pages']),4000)
            archive=Archive(d)
            self.assertEqual(json.loads(''.join(archive.get(v)['text'] for v in refs)),value)
            with self.assertRaises(Failure):repair.read_evidence(['event-'+'0'*64],payload['repair_evidence_catalog'],bundle,cfg)
            path=Path(d)/(refs[0]+'.json');path.write_text('{}')
            with self.assertRaises(Failure):repair.read_evidence(refs[:1],payload['repair_evidence_catalog'],bundle,cfg)
if __name__=='__main__':unittest.main()
