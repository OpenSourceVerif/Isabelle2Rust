"""Validate one immutable prior candidate; no checkpoint migration or generation."""
from copy import deepcopy
from pathlib import Path
from .common import Failure,Executor,save,now
from .segmented_contract import coverage,probes
from .segmented_config import materialize,configure
from .segmented_v8 import compile_crate,connection
from .segmented_support import execute
from .segmented_test_audit import adjudicate
from .validation import check_suite
from . import test_connector



def resolve_config(cfg,state):
    # Same order and rule as knowledge_run.build, without merging any defaults.
    effective=configure(deepcopy(cfg))
    original=effective['testing'].get('transport')
    if original=='auto':effective['testing']['transport']='native-u128' if effective['preprocessing']['numeric_mode']=='checked' else 'dashu-ubig'
    if effective['testing']['transport']!=state['transport']:
        raise Failure('derived_transport_mismatch','Effective wire transport must match the immutable original candidate task',{'configured':original,'effective':effective['testing']['transport'],'original_task':state['transport']})
    return effective,{'configured_transport':original,'effective_transport':effective['testing']['transport'],'source':'same configure then auto/numeric rule as knowledge_run.build','original_task_transport':state['transport']}

def validate(state,frozen,project,references,inputs,cfg,provider,work):
    work=Path(work);executor=Executor(work/'commands');original=deepcopy(state['files']);rc=state['rust_config']
    report={'role':'derived_original_candidate_validation','fresh_generation':False,'started_at':now(),'steps':[]}
    def step(name,result):
        report['steps'].append({'phase':name,'result':result,'at':now()})
        save(work/'progress.json',{**report,'model_calls':provider.calls,'usage':provider.usage})
        if result.get('status')!='passed':raise Failure(result.get('status','derived_validation_failed'),name,result)
    try:
        cfg,resolution=resolve_config(cfg,state);report['configuration_resolution']=resolution
        save(work/'effective-config.json',cfg)
        roots=[n for unit in state['partition']['units'].values() for n in unit['members']]
        step('coverage',coverage(state['bundle'],original,state['mapping'],roots,state['partition'],True))
        crate=materialize(work/'candidate',{**original,'src/lib.rs':original['src/lib.rs']+probes(state['mapping'])},rc)
        step('compile',compile_crate(crate,rc,cfg,executor))
        failed=execute(frozen,crate,rc,cfg,executor)
        report['original_support_replay']=failed;save(work/'original-support-replay.json',failed)
        if failed['status']=='support_test_compile_failed':
            # Only the mechanically proved revision is allowed here. If it is
            # not applicable, stop rather than start a fresh oracle discussion.
            from .segmented_test_audit import exhaustiveness_revision
            if exhaustiveness_revision(frozen,failed,state) is None:raise Failure('unsupported_derived_support_failure','No exact mechanical revision',failed)
            revision=adjudicate(frozen,failed,state,cfg,provider,work/'support-audit')
            frozen=revision['frozen'];save(work/'revised-frozen.json',frozen)
            step('support',execute(frozen,crate,rc,cfg,executor))
        else:step('support',failed)
        previous=None;feedback=None;built=None
        for attempt in range(cfg['v8']['connector_stall_limit']):
            directory=work/f'connector-{attempt+1:03d}'
            files,_=test_connector.connect(project,crate,original,state['mapping'],{'dependencies':rc['dependencies'],'rust_config':rc},cfg,provider,directory,previous,feedback,context_directory=work/'connector-context')
            built=compile_crate(connection(crate,files,rc,cfg),rc,cfg,executor,False)
            report['steps'].append({'phase':'connector_compile','attempt':attempt+1,'result':built,'at':now()})
            save(work/'progress.json',{**report,'model_calls':provider.calls,'usage':provider.usage})
            if built['status']=='passed':break
            previous=files;feedback=built
        else:raise Failure('connector_stalled','Derived binding did not compile',built)
        # Force actual OCaml and Stage2 executions instead of reusing output
        # caches. Inputs remain the exact original fixed/generated lists.
        refs=deepcopy(references)
        for name in ['ocaml','stage2']:refs[name].pop('outputs_path',None)
        for name in ['fixed','generated']:
            if not inputs[name]:continue
            for prefix,args in [('',()),('kernel_',('--i2r-kernel-check',))]:
                step(prefix+name,check_suite(state['bundle']['case'],inputs[name],built['binary'],refs,executor,cfg['testing']['process_timeout'],prefix+name,arguments=args))
        report['status']='passed'
    except Failure as error:
        report.update(status=error.code,error=str(error),error_evidence=error.evidence)
    assert state['files']==original,'Derived validation must never modify the candidate'
    report.update(finished_at=now(),model_calls=provider.calls,usage=provider.usage,candidate_unchanged=True,oracle_identity=frozen.get('oracle_identity',frozen['identity']))
    save(work/'result.json',report)
    return report
