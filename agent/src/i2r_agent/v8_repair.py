"""Executed issue identity and repair progress, independent of textual code changes."""
from copy import deepcopy
from pathlib import Path
import re
from .common import Failure, save
from .task_context import fingerprint
from .segmented_config import cargo_command
from .validation import execute


def validate_config(cfg):
    p=cfg.get('v8',{})
    required={'schema_version','repair_escalate_after','repair_stall_limit',
              'connector_stall_limit','diagnostic_read_limit','performance_refinement',
              'optimization_no_gain_limit','minimum_speedup','maximum_regression',
              'profile_repetitions','profile_timeout','final_failure_policy'}
    if set(p)-{'test_order_policy','unit_policy','correctness_only','small_program_max_entities','small_program_max_source_characters'}!=required or p.get('schema_version')!=1:
        raise Failure('invalid_v8_config','Explicit v8 policy required; unknown/missing fields rejected',sorted(required))
    if type(p.get('correctness_only',False)) is not bool:raise Failure('invalid_v8_config','correctness_only must be boolean')
    from .test_order_policy import configure as configure_order
    configure_order({},cfg)
    from .semantic_components import grouping_policy
    grouping_policy(cfg)
    if p.get('unit_policy','scc') not in {'scc','semantic-components'}:
        raise Failure('invalid_v8_config','unit_policy must be scc or semantic-components')
    for key in ['repair_escalate_after','repair_stall_limit','connector_stall_limit','diagnostic_read_limit',
                'optimization_no_gain_limit','profile_repetitions','profile_timeout']:
        if type(p[key]) is not int or p[key]<=0:raise Failure('invalid_v8_config',key)
    if p['repair_stall_limit']<=p['repair_escalate_after']:raise Failure('invalid_v8_config','Allow diagnosis before stopping')
    for key in ['performance_refinement']:
        if type(p[key]) is not bool:raise Failure('invalid_v8_config',key)
    if p['minimum_speedup']<=1 or p['maximum_regression']<1:raise Failure('invalid_v8_config','Performance thresholds')
    if p['final_failure_policy']!='stop_and_report':raise Failure('invalid_v8_config','Final evaluation is terminal')
    if cfg['source_optimization']['enabled']:
        raise Failure('source_optimization_unimplemented','v8 diagnoses source bottlenecks but does not yet implement source refinement; disable the switch')


def register(state, kind, result, reproducer, return_phase, failure=None):
    ledger=state.setdefault('repair_issues',[])
    key=fingerprint({'kind':kind,'reproducer':reproducer})
    issue=next((r for r in ledger if r['id']==key and r['status']=='open'),None)
    if issue is None:
        returns=sum(r['id']==key for r in ledger)
        issue={'id':key,'kind':kind,'status':'open','reproducer':deepcopy(reproducer),
               'original':deepcopy(result),'latest':deepcopy(result),'return_phase':return_phase,
               'attempts':[],'unsuccessful_replays':0,'observations':[],'reads':0,'recurred_after_resolution':returns}
        ledger.append(issue)
    state['active_issue']=key
    if failure is not None:
        failure['repair_issue']=key
        # An issue id can recur after resolution. Bind this occurrence's
        # evidence too, so replay cannot close a different failure occurrence.
        issue.setdefault('failure_evidence',[]).append(failure['evidence'])
    state['feedback']=result
    return issue


def active(state):
    return next((r for r in reversed(state.get('repair_issues',[])) if r['id']==state.get('active_issue') and r['status']=='open'),None)


def proposal(state, reply):
    issue=active(state)
    if not issue:return
    h=reply.get('repair_hypothesis',{})
    if not isinstance(h,dict) or any(not isinstance(h.get(k),str) or not h[k].strip() for k in ['cause','evidence','change','prediction']):
        raise Failure('missing_repair_hypothesis','Provide repair_hypothesis:{cause,evidence,change,prediction}; use the exact original reproducer')
    normalized=re.sub(r'\W+',' ',h['cause'].lower()).strip()
    observation_count=len(issue['observations'])
    if any(a.get('cause_key')==normalized and a.get('outcome') not in {None,'passed'} and a.get('observations')==observation_count for a in issue['attempts']):
        raise Failure('repeated_repair_hypothesis','This explanation already failed without new executed observations. Request diagnostics or change the explanation.',issue['attempts'])
    issue['attempts'].append({'hypothesis':deepcopy(h),'cause_key':normalized,'observations':observation_count})


def replay_result(state,result,cfg,*,verified_version=None,evidence=None):
    issue=active(state)
    if not issue:raise Failure('missing_repair_issue','A replay must be bound to an open issue')
    issue['latest']=deepcopy(result);issue['reads']=0
    if issue['attempts']:
        issue['attempts'][-1]['outcome']=result['status']
        issue['attempts'][-1]['result']=deepcopy(result)
    if result['status']=='passed':
        issue['status']='replayed_passed'
        for failure in state.get('failures',[]):
            if (failure.get('status')=='open' and failure.get('repair_issue')==issue['id']
                    and failure.get('evidence') in issue.get('failure_evidence',[])):
                failure.update(status='closed',verified_version=verified_version,
                               replay_evidence=evidence)
        return True
    issue['unsuccessful_replays']+=1
    if issue['unsuccessful_replays']>=cfg['v8']['repair_stall_limit']:
        raise Failure('repair_stalled','Original issue remains unresolved after diagnostic escalation; code changes do not reset this limit',issue)
    return False


def needs_diagnostics(state,cfg):
    issue=active(state)
    if not issue:return False
    n=issue['unsuccessful_replays']
    return n>=cfg['v8']['repair_escalate_after'] and not any(x.get('after_replay')==n for x in issue['observations'])


def diagnostic(state,cfg,executor,directory):
    """Replay the exact batch/path. Debug is supplementary, never acceptance."""
    issue=active(state)
    if not issue:raise Failure('missing_repair_issue','No current failure for diagnostic replay')
    path=Path(directory);path.mkdir(parents=True,exist_ok=True)
    result={'issue':issue['id'],'after_replay':issue['unsuccessful_replays'],
            'scope':'Supplementary diagnosis; only release/original-condition replay can close an issue',
            'reproducer':issue['reproducer']}
    if issue['kind']=='behavior' and state.get('harness'):
        rc=state['rust_config'];crate=Path(state['harness'])
        command=cargo_command(rc,cfg,'build',crate,'--message-format=json')
        # Separate artifacts from acceptance builds, while preserving cfg/features/target.
        command[command.index('--target-dir')+1]=str(path/'target')
        built=executor.run(command,env={'RUST_BACKTRACE':'full'},timeout=cfg['budgets']['build_seconds'],check=False)
        result['build']=built
        if built['status']=='passed':
            target=path/'target'
            if rc['target']:target/=rc['target']
            rep=issue['reproducer']
            binary=target/'debug/i2r_harness'
            wire=''.join(' '.join(map(str,x))+'\n' for x in rep['inputs'])
            run=executor.run([binary,*rep['arguments']],stdin=wire,env={'RUST_BACKTRACE':'full'},timeout=rep['timeout'],check=False)
            result.update(execution=run,stdout=Path(run['stdout']).read_text(),stderr=Path(run['stderr']).read_text())
    else:
        result['diagnostic']=deepcopy(issue['latest'])
        result['note']='Direct support/compile failure: its own actual diagnostics are authoritative; no unrelated harness replay.'
    save(path/'diagnostic.json',result)
    issue['observations'].append({**result,'path':str(path/'diagnostic.json')})
    return result


def targeted_material(state):
    issue=active(state)
    if not issue:return {}
    from .repair_knowledge import compiler
    return compiler(issue['latest'],state.get('rust_config',{}))


def redirect_connector(state, candidate_version, reply=None):
    """A source-based repair may identify an alleged API defect as binding-only.

    Reclassification is not acceptance. Only a subsequent actual harness build
    and all scheduled dual-reference suites on this unchanged candidate close it.
    """
    issue=active(state)
    from .test_order_policy import source_first
    from .source_failure_check import lock
    source_pending=(source_first(state) and
        (state.get('support_evidence',{}).get('status')!='passed' or
         state.get('support_pass_candidate')!=lock(state)))
    if issue and issue['kind']=='support' or source_pending:
        raise Failure('invalid_repair_scope',
            'repair_connection addresses only the differential driver, not frozen source-test bindings. '
            'The current source obligation is unresolved: stay in candidate repair. No candidate edits, '
            'mapping or strategy updates in this repair_connection reply were applied. '
            'If candidate code/API must change, return action=generate with a grounded repair_hypothesis '
            'and the explicit candidate transaction; its original source suite must then compile and execute. '
            'Any resulting source binding failure returns to protected source audit. Do not edit test expectations '
            'or claim a source pass; if no supported safe repair exists, report needs_user.',
            {'active_issue':issue['id'] if issue else None,'issue_kind':issue.get('kind') if issue else None,
             'source_status':state.get('support_evidence',{}).get('status'),
             'candidate_version':candidate_version,
             'unapplied_fields':[k for k in ['files','edits','mapping','rust_config','remove_files','strategy_updates'] if (reply or {}).get(k)]})
    if issue and issue['kind']=='compile' and issue['original'].get('status')=='connector_algorithm_defect':
        issue['connector_recheck']={'candidate_version':candidate_version,
            'scenarios':deepcopy(state.get('connector_scenarios',{}))}


def close_redirected_connector(state, candidate_version, compiled, suites, expected_suites, evidence):
    if compiled.get('status')!='passed' or not suites or not expected_suites:return
    if len(suites)!=len(expected_suites) or {s.get('kind') for s in suites}!=set(expected_suites):return
    if any(s.get('status')!='passed' for s in suites):return
    for issue in state.get('repair_issues',[]):
        bound=issue.get('connector_recheck')
        if (issue.get('status')!='open' or issue.get('kind')!='compile'
                or issue.get('original',{}).get('status')!='connector_algorithm_defect'
                or bound!={'candidate_version':candidate_version,'scenarios':state.get('connector_scenarios',{})}):continue
        issue['status']='verified_passed'
        issue['latest']={'status':'passed','scope':'redirected connector build and full scheduled behavior',
            'candidate_version':candidate_version,'connector_version':fingerprint(state['connector']),
            'scenario_identity':deepcopy(state.get('connector_scenarios',{})),
            'suites':list(expected_suites),'evidence':evidence}


def bounded_evidence(payload,bundle,cfg):
    """Keep failure decisions inline; archive exact bulky evidence once, in bounded pages."""
    import json
    from .task_context import Archive
    archive=Archive(bundle['_context_archive']);catalog={}
    fields={'immutable_test_sources','immutable_unit_tests','obligations','diagnostic','executed_tests'}
    size=min(4000,cfg['segmented']['initial_source_characters'])
    def visit(value):
        if isinstance(value,list):return [visit(v) for v in value]
        if not isinstance(value,dict):return value
        result={}
        for key,item in value.items():
            text=json.dumps(item,ensure_ascii=False)
            if key in fields and len(text)>1000 and (key!='diagnostic' or isinstance(item,str)):
                pages=[]
                for start in range(0,len(text),size):
                    page={'text':text[start:start+size],'part':start//size+1,'parts':(len(text)+size-1)//size,
                          'value_sha256':fingerprint(item),'encoding':'exact-json-segment'}
                    version=archive.put('event',page);pages.append(version)
                    catalog[version]={'id':version,**{k:v for k,v in page.items() if k!='text'},'characters':len(page['text'])}
                result[key]={'archived_value_sha256':fingerprint(item),'characters':len(text),'pages':pages,
                             'notice':'Exact evidence retained; request_evidence_pages reads bounded segments. Join ordered text and JSON-decode.'}
                if key=='diagnostic':result[key]['diagnostic_excerpt']=item[:1200]
            else:result[key]=visit(item)
        return result
    for key in ['feedback','open_failures','repair_issue']:
        payload[key]=visit(payload.get(key))
    payload['repair_evidence_catalog']=list(catalog.values())
    payload['repair_evidence_protocol']='request_evidence_pages:[exact id,...]. Bounded reads return pending_evidence_pages. Original failing status, missing test bindings and counts remain inline. Archived expectations are immutable.'
    return payload


def read_evidence(request,catalog,bundle,cfg):
    from .task_context import Archive
    from .segmented_context import read_pages
    known={row['id']:row for row in catalog}
    if set(request)-set(known):raise Failure('unknown_material','Choose exact repair_evidence_catalog page IDs')
    archive=Archive(bundle['_context_archive'])
    pages={name:{'id':name,**archive.get(name)} for name in request}
    result=read_pages(pages,request,min(8000,cfg['segmented']['initial_source_characters']))
    return {'evidence_pages':result['pages'],'pending_evidence_pages':result['pending_pages']}
