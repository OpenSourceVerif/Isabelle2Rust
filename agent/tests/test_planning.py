import copy
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from i2r_agent.common import ROOT, Failure, config
from i2r_agent.planning import (validate_plan, candidate_contract, manifest, prepare_plan,
                                require_generation_capabilities, numeric_policy)
from i2r_agent.generation import generate


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

    def test_format_failure_retains_previous_plan_and_diagnostics(self):
        invalid=copy.deepcopy(self.plan);invalid['architecture']['exports'][0]['source']='wrong'
        provider=Mock();provider.call.side_effect=[invalid,Failure('invalid_model_response','JSON invalid'),self.plan]
        executor=Mock();cfg=config();cfg['preprocessing']['include_adapter_reference']=False
        with tempfile.TemporaryDirectory() as tmp, patch('i2r_agent.adapters.load_adapter',return_value={'status':'loaded','audit':{},'after_target':self.bundle['programs'][0]}) as load:
            bundle,result=prepare_plan(self.bundle,cfg,provider,tmp,executor)
            last=json.loads(provider.call.call_args_list[2].args[1])
            self.assertEqual(last['previous_plan'],invalid)
            self.assertEqual([x['status'] for x in last['feedback']],['invalid_model_response'])
            self.assertEqual(result['status'],'passed')
            load.assert_called_once()
            self.assertEqual(provider.call.call_args.kwargs['phase'],'preprocessing')

    def test_generation_can_revise_representation_without_fixed_helpers(self):
        new=copy.deepcopy(self.plan);new['adaptation']['numeric']='u64';new['adaptation']['decisions'][0]['representation']='u64'
        provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'pub fn observe() {}'},'mapping':[],
            'adaptation_usage':[],'revised_plan':new,'plan_revision_reason':'checked narrower domain'}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Failure) as e:
                generate({**self.bundle,'translation_plan':self.plan},config(),provider,tmp)
            self.assertEqual(e.exception.code,'adapter_revision_requested')
            self.assertEqual(e.exception.evidence,new)
            self.assertFalse((Path(tmp)/'src/lib.rs').exists())

    def test_source_only_still_explicitly_receives_plan_and_numeric_mode(self):
        from i2r_agent.generation import generation_context
        context=generation_context({**self.bundle,'translation_plan':self.plan},'source_only')
        self.assertIn('translation_plan',context);self.assertNotIn('programs',context)

    def test_numeric_default_and_invalid_setting(self):
        self.assertEqual(numeric_policy(config())['mode'],'checked')
        with self.assertRaises(Failure):numeric_policy({'preprocessing':{'numeric_mode':'silently-wrap'}})


if __name__=='__main__':unittest.main()
