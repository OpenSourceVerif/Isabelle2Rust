import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from i2r_agent.common import config, Executor, Failure
from i2r_agent.preprocessing import preprocess
from i2r_agent.generation import generation_context
from i2r_agent.validation import execute,check_suite
from i2r_agent.provider import Provider

class PreprocessingEvidenceTests(unittest.TestCase):
    def test_missing_equations_remain_visible_without_ocaml_ffi_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/'project';project.mkdir();(project/'Export.thy').write_text('theory Export imports Main begin end')
            export=root/'export';export.mkdir()
            graph={'schema_version':1,'entries':['constant:X.f'],'nodes':[{'id':'constant:X.f','statement':{'kind':'unimplemented'},'dependencies':[]}],'sccs':[['constant:X.f']]}
            for file in ['program.json','before-target.json','ocaml-after.json']:(export/file).write_text(json.dumps(graph))
            (export/'adapter-bindings.json').write_text(json.dumps({'types':[],'operations':[],'support_modules':[]}))
            (export/'source-model.json').write_text(json.dumps({'schema_version':1,'entries':['constant:X.f'],
                'entities':[{'id':'constant:X.f','name':'X.f','kind':'constant','dependencies':[], 'execution_equations':None}]}))
            (export/'target-evidence.json').write_text(json.dumps({'target':'OCaml','status':'captured'}))
            (export/'ocaml-evidence-0.txt').write_text('let f x = External.foo x')
            cfg=config();cfg['preprocessing']['include_adapter_reference']=False
            with patch('i2r_agent.preprocessing.build_project',return_value=export):
                bundle=preprocess(project,cfg,root/'work',Mock())
            self.assertEqual(bundle['programs'][0]['nodes'],graph['nodes'])
            self.assertEqual(bundle['external_inventory'],[])
            self.assertEqual(bundle['program_inventory']['unresolved_code_equations'],['constant:X.f'])
            context=generation_context(bundle,'structured')
            packed=context['programs']
            def expand(value):
                if isinstance(value,dict) and set(value)=={'$ref'}:return expand(packed['table'][value['$ref']])
                if isinstance(value,dict):return {k:expand(v) for k,v in value.items()}
                if isinstance(value,list):return [expand(v) for v in value]
                return value
            decoded=expand(packed['root'])
            self.assertNotIn('target_evidence',context)
            self.assertEqual(decoded,bundle['programs'])
            self.assertNotIn('External.foo',json.dumps(context))
            self.assertNotIn('adapter_reference',context)

    def test_generation_preserves_graph_without_repeating_concrete_applications(self):
        from test_planning import fixture
        bundle,plan=fixture();term={'kind':'application','children':[{'symbol':'constant:M.observe'}]*100}
        applications=[{'owner':'constant:M.observe','thingol':term,'application':{'status':'rendered','rust':'f(x)'}} for _ in range(200)]
        bundle['loaded_adapter']={'bindings':{'concrete_applications':applications},'before_target':bundle['programs'][0],'after_target':bundle['programs'][0]}
        context=generation_context(bundle,'structured');packed=context['programs']
        def expand(value):
            if isinstance(value,dict) and set(value)=={'$ref'}:return expand(packed['table'][value['$ref']])
            if isinstance(value,dict):return {k:expand(v) for k,v in value.items()}
            if isinstance(value,list):return [expand(v) for v in value]
            return value
        self.assertEqual(expand(packed['root']),bundle['programs'])
        self.assertNotIn('concrete_applications',context['effective_bindings'])
        self.assertEqual(len(bundle['loaded_adapter']['bindings']['concrete_applications']),200)
        self.assertLess(len(json.dumps(context)),len(json.dumps(bundle))//4)

    def test_range_exceeded_is_not_success_or_behavioral_counterexample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bad=root/'bad';good=root/'good'
            bad.write_text('#!/usr/bin/env python3\nimport sys\nprint("I2R_NUMERIC_OVERFLOW",file=sys.stderr)\nsys.exit(1)\n')
            good.write_text('#!/usr/bin/env python3\nimport sys\nfor x in sys.stdin:print(1)\n')
            bad.chmod(0o755);good.chmod(0o755)
            refs={k:{'binary':str(good)} for k in ['ocaml','stage2']}
            result=check_suite('ackermann',[[0,0]],str(bad),refs,Executor(root/'logs'),5,'range')
            self.assertEqual(result['status'],'numeric_range_exceeded')
            self.assertEqual(result['counterexamples'],[])
            self.assertIsNone(result['failures'])

    def test_provider_preserves_raw_response_for_narrow_json_recovery(self):
        import io
        raw={'choices':[{'finish_reason':'stop','message':{'content':'{"a": 1}}'}}]}
        with tempfile.TemporaryDirectory() as tmp, patch('i2r_agent.provider.credential',return_value='test'), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
            provider=Provider(config(),tmp)
            self.assertEqual(provider.call('s','p'),{'a':1})
            self.assertEqual(json.loads((Path(tmp)/'001/response.json').read_text()),raw)
            self.assertTrue((Path(tmp)/'001/format-normalizations.json').exists())

if __name__=='__main__':unittest.main()
