from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .common import Failure,save,read
from .preprocessing import preprocess
from .performance import benchmark
from .suites import scoped_performance_input,input_bits
from .validation import reference_outputs
from .generation import generation_context


def kernel_contract(project):
    text=(Path(project)/'Kernel.thy').read_text()
    match=re.search(r'definition kernel_run :: "([^"\n]+)" where\s*"kernel_run (\w+) = ',text)
    if not match:raise Failure('unsupported_source_optimization','Expected a declared kernel_run type and one argument')
    return {'type':match[1],'variable':match[2],'source':text}


def check_proposal(project,response,cfg,directory,executor):
    expression=response['expression'];proof=response['proof']
    prohibited=r'\b(sorry|oops|axiomatization|axioms|oracle|ML|setup|method_setup|attribute_setup|declare|lemma|theorem|definition|end|begin|skip_proofs)\b'
    if re.search(prohibited,expression+' '+proof) or '"' in expression or not proof.lstrip().startswith('by '):
        raise Failure('invalid_source_proposal','Proposal contains unsupported proof commands')
    overlay=Path(directory)/'project';shutil.copytree(project,overlay)
    contract=kernel_contract(project)
    variable=contract['variable']
    if 'lemma kernel_observation:' in contract['source']:
        observation_proof='by (simp add: agent_equivalence Kernel.kernel_observation)'
    else:
        observation_proof=('by (cases input) (simp_all add: agent_equivalence Kernel.kernel_prepare_def '
            'Kernel.kernel_run_def Kernel.kernel_encode_def Model.observe_def Let_def split: prod.splits option.splits)')
    (overlay/'Optimization.thy').write_text('theory Optimization\n imports Kernel\nbegin\n'
        'definition kernel_run :: "'+contract['type']+'" where\n'
        ' "kernel_run '+variable+' = '+expression+'"\n'
        'lemma agent_equivalence: "kernel_run '+variable+' = Kernel.kernel_run '+variable+'"\n'+proof+'\n'
        'lemma agent_observation_code [code]:\n'
        ' "Model.observe input = Kernel.kernel_encode (kernel_run (Kernel.kernel_prepare input))"\n'
        +observation_proof+'\nend\n')
    original=(overlay/'Export.thy').read_text()
    original=original.replace('imports Kernel','imports Optimization').replace('Kernel.kernel_run','Optimization.kernel_run')
    (overlay/'Export.thy').write_text(original)
    metadata=read(overlay/'case.json');metadata['kernel']['run']='Optimization.kernel_run'
    save(overlay/'case.json',metadata)
    proof_cfg={**cfg,'budgets':{**cfg['budgets'],'build_seconds':cfg['source_optimization']['proof_timeout']}}
    return overlay,preprocess(overlay,proof_cfg,Path(directory)/'preprocessing',executor)


def optimize(project,bundle,case,crate,binary,cfg,provider,work,executor,references,fixed_inputs,random_inputs,regressions,update):
    from .pipeline import search
    record={'status':'no_candidate','proposals':[],'original_project':str(project)}
    parent_crate,parent_binary=crate,binary
    workload=scoped_performance_input(case,input_bits(cfg))
    expected=reference_outputs(case,[workload],references,executor,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
    baseline=benchmark({'parent':binary},workload,expected,cfg,executor,work/'optimization-baseline')
    update({'phase':'source_optimization','source_optimization':record})
    for number in range(cfg['source_optimization']['max_proposals']):
        directory=work/f'source-proposal-{number+1:02d}';directory.mkdir()
        proposal={'number':number+1,'status':'proposing'};record['proposals'].append(proposal)
        try:
            response=provider.call('''Return JSON for one small Isabelle/HOL optimization of Kernel.kernel_run, using existing proof automation.
The supplied kernel_contract gives its exact type, argument name and original source.
Return {"skip":true,"reason":"..."} or {"expression":"HOL expression using that argument","proof":"by ...","reason":"..."}.
The system defines Optimization.kernel_run with the same type and requires the theorem
Optimization.kernel_run argument = Kernel.kernel_run argument. Use kernel_run_def to unfold the new definition.
Preserve inputs, outputs, shape/order, numeric semantics and assumptions. Preparation and encoding stay unchanged.
No sorry, oops, axiomatization, ML, oracle or unchecked facts. This is optional, bounded optimization, not general proof research.
Use the measured Rust evidence and source equations. Failure keeps the original implementation.''',
                json.dumps({'kernel_contract':kernel_contract(project),'program':generation_context(bundle,'structured'),
                            'performance':baseline,'rust':(crate/'src/lib.rs').read_text()},ensure_ascii=False),phase='source_optimization')
            save(directory/'proposal.json',response)
            if response.get('skip'):
                proposal.update(status='skipped',reason=response.get('reason'));continue
            overlay,optimized=check_proposal(project,response,cfg,directory,executor)
            proposal.update(status='proved',theorem='Optimization.agent_equivalence',
                observation_theorem='Optimization.agent_observation_code',project=str(overlay))
            if cfg.get('preprocessing',{}).get('mode')=='auto':
                from .planning import prepare_plan
                optimized,planning=prepare_plan(optimized,cfg,provider,directory/'planning',executor)
                proposal['preprocessing']=planning
            attempts,new_crate,new_binary=search(optimized,case,cfg,provider,directory,executor,references,
                fixed_inputs,random_inputs,regressions,lambda change: update({'phase':'source_optimization','source_optimization':record}))
            proposal['generation_attempts']=attempts
            if new_crate is None:
                proposal['status']='regeneration_failed';continue
            measured=benchmark({'parent':parent_binary,'optimized':new_binary},workload,expected,cfg,executor,directory)
            proposal['performance']=measured
            speedup=measured['summary']['parent']['median_ns']/measured['summary']['optimized']['median_ns']
            proposal['speedup']=speedup
            if speedup>=cfg['source_optimization']['min_speedup']:
                proposal['status']='accepted';record.update(status='accepted',project=str(overlay),selection='single-workload median; exploratory')
                save(work/'source-optimization.json',record)
                return new_crate,new_binary,record
            proposal['status']='no_performance_gain'
        except (Failure,KeyError) as error:
            proposal.update(status='rejected',reason=str(error),error_code=getattr(error,'code','invalid_response'))
        save(work/'source-optimization.json',record)
        update({'phase':'source_optimization','source_optimization':record})
    record['status']='kept_original';save(work/'source-optimization.json',record)
    return parent_crate,parent_binary,record
