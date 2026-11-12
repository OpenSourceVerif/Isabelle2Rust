import copy
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from i2r_agent.common import ROOT, Failure, config
from i2r_agent.planning import validate_plan, candidate_contract, manifest, require_generation_capabilities, numeric_policy


def fixture(mode='checked'):
    bundle={'programs':[{'entries':['constant:M.observe'],'nodes':[{'id':'constant:M.observe','statement':{}},
             {'id':'type:Nat.nat','statement':{}}], 'sccs':[['constant:M.observe'],['type:Nat.nat']]}],
            'sources':{'Model.thy':'test fixture'},'representation':{'mode':'llm_designed'},'contract':'fixture',
            'numeric_policy':{'mode':mode},'external_inventory':[{'id':'external:native'}]}
    plan={'schema_version':3,'numeric_mode':mode,
          'architecture':{'units':[{'id':'main','source_symbols':['constant:M.observe'],'purpose':'original entry'}],
                          'exports':[{'source':'constant:M.observe','intent':'preserve behavior'}],'shared':[]},
          'adaptation':{'numeric':'u128' if mode=='checked' else 'IBig','sequence':'native slice',
                        'decisions':[{'id':'nat','scope':['type:Nat.nat'],'representation':'u128' if mode=='checked' else 'IBig',
                          'operations':[],'domain':'finite checked intermediates' if mode=='checked' else 'arbitrary precision',
                          'overflow':'checked_error' if mode=='checked' else 'arbitrary_precision',
                          'conversions':['checked transport conversion'],'rationale':'program-specific','checks':['boundary conversion']}]},
          'boundaries':[{'id':'external:native','route':'native_replace','implementation':'u128 or chosen bigint','rationale':'source ops','checks':[]}],
          'dependencies':{},'support_requirements':[],'open_questions':[],
          'adapter':{'imports':[],'declarations':'','rust_files':{},'rust_root':''}}
    return bundle,plan


class PlanningTests(unittest.TestCase):
    def setUp(self):self.bundle,self.plan=fixture()

    def test_machine_integer_plan_needs_no_fixed_probe_menu(self):
        self.assertEqual(validate_plan(self.plan,self.bundle)['status'],'passed')
        self.assertNotIn('adapter_files',self.plan)
        self.assertNotIn('probe_operations',self.plan['adaptation'])

    def test_arbitrary_library_choice_is_open_but_mode_must_match(self):
        bundle,plan=fixture('arbitrary');plan['dependencies']={'dashu-int':{'version':'=0.6.2','features':['std'],'default-features':False}}
        validate_plan(plan,bundle)
        with self.assertRaises(Failure):validate_plan(plan,self.bundle)
        parsed=tomllib.loads(manifest(plan['dependencies']))
        self.assertFalse(parsed['dependencies']['dashu-int']['default-features'])

    def test_entry_and_real_source_references(self):
        self.plan['architecture']['exports']=[]
        with self.assertRaises(Failure):validate_plan(self.plan,self.bundle)
        _,self.plan=fixture();self.plan['adaptation']['decisions'][0]['scope']=['invented']
        with self.assertRaises(Failure):validate_plan(self.plan,self.bundle)

    def test_external_symbols_survive_planning_as_capability_gaps(self):
        self.plan['boundaries'][0]['route']='retain_ffi'
        self.assertEqual(len(validate_plan(self.plan,self.bundle)['capability_gaps']),0)
        require_generation_capabilities(self.plan)
        self.plan['boundaries'][0]['route']='unresolved'
        with self.assertRaises(Failure) as e:require_generation_capabilities(self.plan)
        self.assertEqual(e.exception.code,'generation_capability_gap')
        self.plan['boundaries']=[]
        with self.assertRaises(Failure):validate_plan(self.plan,self.bundle)

    def test_native_inline_mapping_no_forced_module_or_signature(self):
        files={'src/lib.rs':'pub fn observe(x: &[u128]) -> Vec<u128> { x.to_vec() }'}
        result=candidate_contract(self.plan,files,[{'source':'constant:M.observe','rust':'observe'},{'source':'type:Nat.nat','rust':'u128'}],
            [{'decision':'nat','locations':['src/lib.rs: observe'],'implementation':'native inline operation'}],self.bundle)
        self.assertEqual(result['status'],'recorded')
        with self.assertRaises(Failure):candidate_contract(self.plan,files,[],[],self.bundle)

    def test_schema_and_versions_are_checked(self):
        with self.assertRaises(Failure):manifest({'ibig':'*'})
        self.plan['explanation']='Extra descriptive text is harmless'
        validate_plan(self.plan,self.bundle)
        self.plan['schema_version']=2
        with self.assertRaises(Failure):validate_plan(self.plan,self.bundle)


    def test_numeric_default_and_invalid_setting(self):
        self.assertEqual(numeric_policy(config())['mode'],'checked')
        with self.assertRaises(Failure):numeric_policy({'preprocessing':{'numeric_mode':'silently-wrap'}})


if __name__=='__main__':unittest.main()
