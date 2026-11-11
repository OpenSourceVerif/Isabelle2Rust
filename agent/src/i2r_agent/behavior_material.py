"""Exact observation context for behavior diagnosis; no candidate edit authority."""
from copy import deepcopy
from pathlib import Path
from .common import Failure,read,digest
from .task_context import fingerprint


def wire_contract(cfg):
    transport=cfg['testing']['transport']
    from .test_connector import TYPES,driver
    if transport not in TYPES:raise Failure('unsupported_transport',transport)
    raw=driver(transport,timing=not bool(cfg.get('v8',{}).get('correctness_only')))
    return {'transport':transport,'rust_type':TYPES[transport],
        'driver_source':raw,'driver_identity':fingerprint(raw),
        'instruction':'The actual shared driver below is authoritative for parsing and serialization. Wire values enter observe/benchmark_prepare directly in this type. Do not assume a global tagged or zigzag encoding. Apply only conversions required by the actual Model/Kernel source equations and this driver; model diagnostic hypotheses are unverified.'}


def share_reports(payload):
    """Intern only exact whole executed behavior reports, never similar evidence."""
    out=deepcopy(payload);reports={}
    def visit(v):
        if isinstance(v,list):return [visit(x) for x in v]
        if not isinstance(v,dict):return v
        if {'status','references','candidate','counterexamples'}<=set(v):
            key=fingerprint(v)
            if key in reports and reports[key]!=v:raise Failure('behavior_evidence_changed','Report digest collision')
            reports[key]=deepcopy(v)
            return {'behavior_report_ref':key}
        return {k:visit(x) for k,x in v.items()}
    for key in ['feedback','open_failures','repair_issue']:
        if key in out:out[key]=visit(out[key])
    out['behavior_reports']=reports
    out['behavior_report_protocol']='Every behavior_report_ref resolves to the exact complete report in behavior_reports by content identity. Multiple references share only byte-equivalent JSON values; differing original/latest reports remain separate. All counterexamples, reference coverage and raw artifact paths are retained. These are observations, never permission to change the candidate lock or expectations.'
    return out


def restore_reports(payload):
    """Mechanical inverse used by evidence validation and regression checks."""
    reports=payload['behavior_reports']
    def visit(v):
        if isinstance(v,list):return [visit(x) for x in v]
        if not isinstance(v,dict):return v
        if set(v)=={'behavior_report_ref'}:
            key=v['behavior_report_ref'];value=reports.get(key)
            if value is None or fingerprint(value)!=key:raise Failure('behavior_evidence_changed','Missing or changed exact report',key)
            return deepcopy(value)
        return {k:visit(x) for k,x in v.items()}
    return {k:visit(v) for k,v in payload.items() if k not in {'behavior_reports','behavior_report_protocol'}}


def augment(payload,state,cfg,project,work,executor):
    from .observation_source import acquire,ownership_for
    if project is None:raise Failure('observation_source_changed','Behavior diagnosis requires the actual observation project')
    project=Path(project)
    scenarios={name:(project/name).read_text() for name in ['Model.thy','Kernel.thy']}
    hashes={name:digest(project/name) for name in scenarios}
    if hashes!=state.get('connector_scenarios'):raise Failure('observation_source_changed','Current wrapper differs from executed connector scenario identity')
    helpers=acquire(project,state['bundle']['source_model'],cfg,Path(work)/'observation-source',executor,
                    ownership=ownership_for(state['bundle']['source_model'],state['partition']))
    context={'schema':'behavior-observation-material-v1','scenario_sources':scenarios,'scenario_hashes':hashes,
        'connector_files':deepcopy(state.get('connector',{})),'connector_identity':fingerprint(state.get('connector',{})),
        'candidate_lock':state.get('source_candidate_lock'),'candidate_files_identity':fingerprint(state['files']),
        'candidate_mapping_identity':fingerprint(state['mapping']),'source_identity':fingerprint(state['bundle']['source_model']),
        'input_contract':read(project/'case.json').get('contract','') if (project/'case.json').exists() else '',
        'wire_contract':wire_contract(cfg),'observation_helpers':helpers,
        'authority':'Inspect actual candidate calls, current connector and source observation before diagnosing the cause. Counterexamples alone do not define the wrapper. Distinguish binding conversion/call defects from candidate defects. Existing immutable candidate/source-test/reference guards and action authority are unchanged; repair_connection requests connector work only, never acceptance.'}
    context['identity']=fingerprint(context)
    result=deepcopy(payload);result['behavior_observation']=context
    return share_reports(result)
