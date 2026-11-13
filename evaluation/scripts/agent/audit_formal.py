#!/usr/bin/env python3
"""Read-only audit of the active frozen run. Writes only the migrated run integration-audit.json.
No experiment execution, model calls, subprocesses, repairs or state mutation.
"""
import collections, copy, hashlib, json, math, os, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
B = REPO/'artifact/runs/unit-formal-20261113-r2'
FPP_RUN = REPO/'artifact/runs/fpp-formal-clean-20261113'
FPP_SOURCE = FPP_RUN/'frozen-source'
BACKENDS = ('ocaml', 'stage1', 'stage2')
TOKEN_KEYS = ('prompt_tokens', 'completion_tokens', 'total_tokens')
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(x): return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
def optional(p, default=None): return read(p) if Path(p).is_file() else default

def coverage(suites, check_candidate=False):
    counts=collections.Counter(); combinations=collections.Counter(); errors=[]; receipts=[]
    for label,s in suites:
        cov=s.get('reference_coverage',s.get('selection',{})); matrix=cov.get('matrix')
        if not isinstance(matrix,list):
            errors.append({'suite':label,'error':'missing_per_input_reference_matrix'});continue
        expected_count=s.get('count',cov.get('total'))
        if len(matrix)!=expected_count: errors.append({'suite':label,'error':'matrix_count_mismatch'})
        actual=None
        if check_candidate and s.get('status')=='passed':
            rec=s.get('candidate',{})
            try:
                actual=[[int(n) for n in line.split()] for line in Path(rec['stdout']).read_text().splitlines()]
                receipts.append({'suite':label,'candidate_stdout':rec['stdout'],'sha256':sha(rec['stdout'])})
                if rec.get('status')!='passed' or rec.get('returncode')!=0 or len(actual)!=len(matrix):raise ValueError('candidate receipt/count mismatch')
            except Exception as e: errors.append({'suite':label,'error':'candidate_receipt_unverified','detail':str(e)})
        for index,row in enumerate(matrix):
            refs=row.get('references',{}); available=[k for k in BACKENDS if refs.get(k,{}).get('status')=='passed' and refs[k].get('output') is not None]
            counts[str(len(available))]+=1;combinations['+'.join(available) or 'none']+=1
            if sorted(available)!=sorted(row.get('available',[])):errors.append({'suite':label,'input_index':index,'error':'available_list_mismatch'})
            outputs=[refs[k]['output'] for k in available]
            if outputs and any(x!=outputs[0] for x in outputs):errors.append({'suite':label,'input_index':index,'error':'reference_conflict'})
            if outputs and row.get('expected')!=outputs[0]:errors.append({'suite':label,'input_index':index,'error':'expected_selection_mismatch'})
            if s.get('status')=='passed' and not available:errors.append({'suite':label,'input_index':index,'error':'passed_without_reference'})
            if actual is not None and index<len(actual) and outputs and actual[index]!=row['expected']:errors.append({'suite':label,'input_index':index,'error':'candidate_output_mismatch'})
            # Inspect runtime output receipts, not compilation availability.
            for k in available:
                item=refs[k];rec=item.get('record',{})
                try:
                    vals=[[int(n) for n in line.split()] for line in Path(rec['stdout']).read_text().splitlines()]
                    offset=item.get('batch_output_index',0)
                    if rec.get('status')!='passed' or rec.get('returncode')!=0 or vals[offset]!=item['output']:raise ValueError('reference receipt/output mismatch')
                except Exception as e:errors.append({'suite':label,'input_index':index,'backend':k,'error':'reference_receipt_unverified','detail':str(e)})
    return {'input_exposures_by_backend_count':dict(counts),'backend_combinations':dict(combinations),'errors':errors,'candidate_receipts':receipts,'counting':'Suite input exposures; repeated inputs across fixed/generated/kernel suites are intentionally not deduplicated.'}

def normalized_cfg(c):
    c=copy.deepcopy(c)
    for k in ('isabelle_heaps','optimizer_target'):c.get('tools',{}).pop(k,None)
    return c

def implementation_check(snapshot,release):
    comparison=read(B/'implementation-comparison.json')
    fpp=FPP_SOURCE;fr=read(FPP_RUN/'release.json')
    prefixes=('agent/src/','agent/prompts/','agent/isabelle/','agent/references/','agent/config/')
    keys={k for k in release['files'] if k.startswith(prefixes)}|{k for k in fr['files'] if k.startswith(prefixes)}
    diffs=[k for k in sorted(keys) if release['files'].get(k)!=fr['files'].get(k)]
    adapter='agent/src/i2r_agent/fpp_artifact.py'
    old="assert len(data['cases'])==313 and len({r['root'] for r in data['cases']})==313"
    new="assert len(data['cases'])==data['expected_root_count'] and len({(r['root'],r['original_source']) for r in data['cases']})==data['expected_root_count']"
    adapter_ok=(snapshot/adapter).read_text()==(fpp/adapter).read_text().replace(old,new)
    fpp_core_live=[k for k in keys if not (fpp/k).is_file() or sha(fpp/k)!=fr['files'].get(k)]
    cfgs={fp(normalized_cfg(c)) for c in fr['effective_configs'].values()}
    cfg_bad=[k for k,c in release['effective_configs'].items() if fp(normalized_cfg(c)) not in cfgs]
    budget_keys=('per_task_calls','per_task_active_seconds','workers')
    budgets={k:{'unit':release[k],'fpp':fr[k]} for k in budget_keys}
    ok=diffs==[adapter] and adapter_ok and not fpp_core_live and not cfg_bad and all(x['unit']==x['fpp'] for x in budgets.values()) and comparison['fpp_frozen_identity']==fr['identity']
    return {'verified':ok,'comparison_artifact_sha256':sha(B/'implementation-comparison.json'),'fpp_identity':fr['identity'],'unit_identity':release['identity'],'core_differences':diffs,'adapter_exact_cardinality_only_change':adapter_ok,'fpp_core_live_mismatches':fpp_core_live,'effective_config_mismatches':cfg_bad,'excluded_config_fields':['tools.isabelle_heaps','tools.optimizer_target'],'budgets':budgets,'scope':'Core source/prompts/Isabelle extractor/references/config, exact approved admission-cardinality adapter difference, effective config and budgets. Corpus/wrappers are intentionally distinct.'}

def main():
    started=time.time();active=read(B/'active-run.json');run=Path(active['run']);snapshot=run.parents[2]
    release=read(run/'release.json');selection=read(run/'selection.json')['ids'];manifest=read(snapshot/'artifact/fpp-manifest.json');byid={r['id']:r for r in manifest['cases']};ids=release['evaluation_order']
    # Pure existing acceptance invariant checker. Disable bytecode creation and never invoke runners/providers.
    sys.path.insert(0,str(snapshot/'agent/src'))
    from i2r_agent.source_failure_review import require_state
    identity_errors=[]
    for msg,condition in [('active_release_identity',active['identity']==release['identity']),('release_fingerprint',fp(release['files'])==release['identity']),('selection_order',selection==ids),('manifest_selection',set(byid)==set(ids)),('expected_488',len(ids)==488 and len(set(ids))==488)]:
        if not condition:identity_errors.append(msg)
    live_mismatches=[k for k,v in release['files'].items() if not (snapshot/k).is_file() or sha(snapshot/k)!=v]
    inventory=set()
    for relroot in ['agent/src','agent/prompts','agent/isabelle','agent/references','agent/config','artifact']:
        for directory,dirs,names in os.walk(snapshot/relroot):
            dirs[:]=[d for d in dirs if d not in {'runs','__pycache__','.venv','.git'}]
            for name in names:
                if name not in {'local.json','local.toml','.DS_Store'}:inventory.add(str((Path(directory)/name).relative_to(snapshot)))
    inventory_difference=sorted(inventory^set(release['files']))
    if inventory_difference:identity_errors.append('live_file_inventory_changed')
    ledger=read(run/'global-provider-budget.json');ledger_start_identity=fp(ledger);reservations=collections.defaultdict(list)
    for x in ledger['reservations']:reservations[x['case']].append(x)
    if ledger['release_identity']!=release['identity']:identity_errors.append('budget_identity')
    if len(ledger['reservations'])>ledger['limit']:identity_errors.append('global_budget_exceeded')
    if len({r['request'] for r in ledger['reservations']})!=len(ledger['reservations']):identity_errors.append('duplicate_provider_reservations')
    rows=[];totals=collections.Counter();violations=[];pending=[];outcome_sigs={};prep_backend=collections.Counter();diff_backend=collections.Counter()
    for key in ids:
        task=run/'tasks'/key;diag=task/'diagnostics';prep=run/'preparation'/key;op=task/'outcome.json';out=optional(op);ad=optional(prep/'admission.json');row={'case':key,'root':byid[key]['root'],'completed':out is not None};errors=[]
        if out:
            outcome_sigs[key]=sha(op);row.update(status=out.get('result',{}).get('status'),accepted=bool(out.get('policy_accepted')),outcome_sha256=outcome_sigs[key]);totals['completed']+=1;totals['accepted']+=row['accepted']
            if out.get('case')!=key:errors.append('outcome_case_mismatch')
            if not out.get('mechanical_failure') and out.get('implementation_identity')!=release['identity']:errors.append('outcome_identity_mismatch')
            if not out.get('mechanical_failure') and out.get('root')!=byid[key]['root']:errors.append('outcome_root_mismatch')
        else:pending.append(key)
        usage={k:0 for k in TOKEN_KEYS};unknown=[];phases=collections.Counter();requests=[];request_errors=[]
        reserved_paths={x['request'] for x in reservations[key]}
        for p in sorted((diag/'model').glob('*/request.json')):
            requests.append(str(p));resp=optional(p.parent/'response.json');u=resp.get('usage') if isinstance(resp,dict) else None
            if not isinstance(u,dict) or any(type(u.get(k)) not in (int,float) for k in TOKEN_KEYS):unknown.append(str(p))
            if isinstance(u,dict):
                for k in TOKEN_KEYS:
                    if type(u.get(k)) in (int,float):usage[k]+=u[k]
            phases[optional(p.parent/'call-state.json',{}).get('phase','unknown')]+=1
            if str(p) not in reserved_paths:request_errors.append({'request':str(p),'error':'unreserved_request'})
        if len(requests)>release['per_task_calls'] or len(reservations[key])>release['per_task_calls']:request_errors.append({'error':'per_root_call_budget_exceeded'})
        row['requests']={'archived_requests':len(requests),'reserved_attempts':len(reservations[key]),'reservations_without_request':sorted(reserved_paths-set(requests)),'known_usage':usage,'unknown_usage_count':len(unknown),'unknown_usage_requests':unknown,'phase_calls':dict(phases),'errors':request_errors,'cost_accounting':'Count each request path once; transport outcome usage snapshots are cumulative and are not summed.'}
        if out and 'calls' in out and (out['calls']!=len(requests) or out.get('known_usage')!=usage):errors.append('outcome_usage_snapshot_mismatch')
        archives=[]
        for p in sorted(task.glob('transport-outcome-*.json')):
            x=read(p);archives.append({'path':str(p),'sha256':sha(p),'seconds':x.get('seconds'),'status':x.get('result',{}).get('status')})
            if x.get('implementation_identity')!=release['identity']:errors.append('transport_archive_identity_mismatch')
        prep_seconds=sum(read(p).get('seconds',0) for p in (prep/'commands').glob('*.json'))
        final_seconds=out.get('seconds',0) if out else None
        row['timing']={'admission_charged_preparation_seconds':ad.get('seconds') if ad else None,'preparation_recorded_command_seconds':prep_seconds,'transport_archived_segment_seconds':sum(x.get('seconds') or 0 for x in archives),'transport_segments':archives,'final_outcome_segment_seconds':final_seconds,'completed_charged_seconds':(ad['seconds'] if ad else prep_seconds)+sum(x.get('seconds') or 0 for x in archives)+(final_seconds or 0),'unfinished_active_segment_not_included':out is None,'counting':'Preparation charge + archived transport segment durations + final outcome segment duration. Do not sum cumulative model usage from transport archives or double-count diagnostic command times.'}
        ps=[(s,read(prep/(s+'.json'))) for s in ['ordinary_fixed','ordinary_generated','kernel_fixed','kernel_generated'] if (prep/(s+'.json')).is_file()]
        row['preparation_reference_coverage']=coverage(ps);prep_backend.update(row['preparation_reference_coverage']['input_exposures_by_backend_count'])
        for name,suite in ps:
            if [r['input'] for r in suite.get('selection',{}).get('matrix',[])]!=byid[key]['inputs'][name]:errors.append('locked_preparation_inputs_mismatch:'+name)
        if ad:
            if ad.get('config')!=release['effective_configs'][key]:errors.append('admission_config_mismatch')
            if ad.get('seal')!=fp({k:v for k,v in ad.items() if k!='seal'}):errors.append('admission_seal_mismatch')
            for field,h in [('source_cache','source_sha256'),('wrapper','wrapper_sha256'),('baseline_record','baseline_sha256')]:
                if not Path(ad[field]).is_file() or sha(ad[field])!=ad[h]:errors.append('admission_artifact_mismatch:'+field)
        if out and row['accepted']:
            try:
                cp=read(diag/'segmented-checkpoint.json');suites=cp.get('differential_suites',[])
                predicate=out['result']['status']=='passed' and cp.get('support_evidence',{}).get('status')=='passed' and bool(suites) and all(s.get('status')=='passed' for s in suites)
                if not predicate:errors.append('fpp_acceptance_predicate_failed')
                row['source_invariant_check']=require_state(cp,release['effective_configs'][key],diag)
                row['accepted_reference_coverage']=coverage([(s['kind'],s) for s in suites],True);diff_backend.update(row['accepted_reference_coverage']['input_exposures_by_backend_count'])
                if row['accepted_reference_coverage']['errors']:errors.append('accepted_reference_receipt_or_policy_error')
            except Exception as e:errors.append('accepted_invariant_exception:'+str(e))
        row['audit_errors']=errors
        if errors or request_errors:violations.append({'case':key,'errors':errors,'request_errors':request_errors})
        for k in TOKEN_KEYS:totals[k]+=usage[k]
        totals['requests']+=len(requests);totals['unknown_usage_requests']+=len(unknown);totals['preparation_recorded_command_seconds']+=prep_seconds;totals['admission_charged_preparation_seconds']+=ad.get('seconds',0) if ad else 0;totals['transport_archived_segment_seconds']+=row['timing']['transport_archived_segment_seconds'];totals['final_outcome_segment_seconds']+=final_seconds or 0
        rows.append(row)
    ledger_end=read(run/'global-provider-budget.json')
    ending_reserved={x['request'] for x in ledger_end['reservations']}
    for row in rows:
        row['requests']['errors']=[e for e in row['requests']['errors'] if not (e.get('error')=='unreserved_request' and e.get('request') in ending_reserved)]
    violations=[{'case':row['case'],'errors':row['audit_errors'],'request_errors':row['requests']['errors']} for row in rows if row['audit_errors'] or row['requests']['errors']]
    changed=[k for k,v in outcome_sigs.items() if not (run/'tasks'/k/'outcome.json').is_file() or sha(run/'tasks'/k/'outcome.json')!=v]
    completed_after=sum((run/'tasks'/k/'outcome.json').is_file() for k in ids)
    concurrent=bool(changed or completed_after!=totals['completed'] or fp(ledger_end)!=ledger_start_identity)
    controller=optional(run/'status.json',{});quiescent=not controller.get('active') and not controller.get('preparing')
    complete=totals['completed']==len(ids) and quiescent and not concurrent
    totals['generation_segment_seconds']=totals['transport_archived_segment_seconds']+totals['final_outcome_segment_seconds']
    totals['accounted_charged_seconds']=sum(r['timing']['completed_charged_seconds'] for r in rows)
    comparison=implementation_check(snapshot,release)
    extras=sorted(p.parent.name for p in (run/'tasks').glob('*/outcome.json') if p.parent.name not in byid)
    tools=release['tool_sources']; tool_mismatches=[]
    for key,value in tools['files'].items():
        name,relpath=key.split('/',1);path=Path(tools['repositories'][name])/relpath
        if not path.is_file() or sha(path)!=value:tool_mismatches.append(key)
    corpus_mismatches=[name for name,value in manifest['corpus'].items() if not (snapshot/name).is_file() or sha(snapshot/name)!=value]
    comparator=audit_fpp(FPP_RUN,require_state)
    integrity=not tool_mismatches and not corpus_mismatches and not identity_errors and not live_mismatches and not violations and not extras and comparison['verified']
    result={'schema_version':1,'audit_started_unix':started,'audit_finished_unix':time.time(),'run':str(run),'identity':release['identity'],'status':'complete' if complete else 'incomplete','integrity_checks_passed':integrity,'selected_roots':len(ids),'completed':totals['completed'],'accepted':totals['accepted'],'failed':totals['completed']-totals['accepted'],'pending':pending,'final_acceptance_rate':totals['accepted']/len(ids) if complete else None,'observed_completed_acceptance_rate':totals['accepted']/totals['completed'] if totals['completed'] else None,'threshold':.95,'minimum_accepted':math.ceil(.95*len(ids)),'final_target_met':totals['accepted']>=math.ceil(.95*len(ids)) if complete and integrity else None,'totals':dict(totals),'reference_coverage':{'preparation_input_exposures':dict(prep_backend),'accepted_differential_input_exposures':dict(diff_backend),'backend_count_labels':{'3':'ocaml+stage1+stage2','2':'two runtime backends','1':'one runtime backend','0':'no runtime backend'},'qualification':'Three backend names are not three independent implementations; Stage2 derives from Stage1. Available-per-input-v1 can accept one backend, which is explicitly counted as single-backend, never dual-reference.'},'identity_errors':identity_errors,'live_release_file_mismatches':live_mismatches,'live_release_inventory_difference':inventory_difference,'unexpected_outcomes':extras,'acceptance_or_accounting_violations':violations,'same_framework_comparison':comparison,'tool_source_mismatches':tool_mismatches,'corpus_mismatches':corpus_mismatches,'fpp_same_accounting':comparator,'snapshot_consistency':{'outcomes_changed_during_audit':changed,'completed_after_audit':completed_after,'concurrent_completion_detected':concurrent,'controller_quiescent':quiescent,'provider_ledger_changed':fp(ledger_end)!=ledger_start_identity},'per_root':rows,'limitations':['Read-only interval snapshot; while running, request/receipt files and counters can change. Rerun after all workers and preparer finish.','Known token totals exclude unknown provider usage; missing usage is counted, never treated as zero-cost.','Preparation command receipts include heap-lock wait charges, not a pure compute-time measure. Interrupted commands without final receipts and unfinished model segments are not reconstructed as exact durations.','Accepted checks reuse the frozen pure require_state invariant and independently read stored runtime output receipts; no programs/tests/models are rerun.','Reference coverage is per suite input exposure, not a count of unique semantic cases or a proof of equivalence.']}
    target=B/'integration-audit.json';tmp=target.with_suffix('.json.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');tmp.replace(target)
    print(json.dumps({k:result[k] for k in ['status','selected_roots','completed','accepted','integrity_checks_passed','final_acceptance_rate','final_target_met']}));print(str(target))
def audit_fpp(run,require_state):
    release=read(run/'release.json');ids=release['evaluation_order'];totals=collections.Counter();rows=[];errors=[];backend_counts=collections.Counter()
    for key in ids:
        task=run/'tasks'/key;diag=task/'diagnostics';prep=run/'preparation'/key;out=optional(task/'outcome.json');ad=optional(prep/'admission.json');usage={k:0 for k in TOKEN_KEYS};unknown=0;calls=0
        for p in (diag/'model').glob('*/request.json'):
            calls+=1;resp=optional(p.parent/'response.json');u=resp.get('usage') if isinstance(resp,dict) else None
            if not isinstance(u,dict) or any(type(u.get(k)) not in (float,int) for k in TOKEN_KEYS):unknown+=1
            if isinstance(u,dict):
                for k in TOKEN_KEYS:
                    if type(u.get(k)) in (float,int):usage[k]+=u[k]
        archives=[read(p) for p in task.glob('transport-outcome-*.json')];preps=sum(read(p).get('seconds',0) for p in (prep/'commands').glob('*.json'));ts=sum(x.get('seconds',0) for x in archives);final=out.get('seconds',0) if out else 0
        row={'case':key,'completed':out is not None,'accepted':bool(out and out.get('policy_accepted')),'requests':calls,'unknown_usage_count':unknown,'known_usage':usage,'admission_charged_preparation_seconds':ad.get('seconds') if ad else None,'preparation_recorded_command_seconds':preps,'transport_archived_segment_seconds':ts,'final_outcome_segment_seconds':final,'status':out.get('result',{}).get('status') if out else None}
        if out and not out.get('mechanical_failure') and out.get('implementation_identity')!=release['identity']:errors.append({'case':key,'error':'identity_mismatch'})
        if row['accepted']:
            try:
                cp=read(diag/'segmented-checkpoint.json');suites=cp.get('differential_suites',[])
                if out['result']['status']!='passed' or not suites or any(s.get('status')!='passed' for s in suites):raise ValueError('acceptance predicate')
                require_state(cp,release['effective_configs'][key],diag)
                cov=coverage([(s['kind'],s) for s in suites],True);backend_counts.update(cov['input_exposures_by_backend_count'])
                if cov['errors']:errors.append({'case':key,'error':'reference_receipt_or_policy','details':cov['errors']})
                row['accepted_reference_coverage']=cov
            except Exception as e:errors.append({'case':key,'error':str(e)})
        totals['completed']+=row['completed'];totals['accepted']+=row['accepted'];totals['requests']+=calls;totals['unknown_usage_requests']+=unknown;totals['preparation_recorded_command_seconds']+=preps;totals['admission_charged_preparation_seconds']+=ad.get('seconds',0) if ad else 0;totals['transport_archived_segment_seconds']+=ts;totals['final_outcome_segment_seconds']+=final
        for k in TOKEN_KEYS:totals[k]+=usage[k]
        rows.append(row)
    totals['generation_segment_seconds']=totals['transport_archived_segment_seconds']+totals['final_outcome_segment_seconds']
    totals['accounted_charged_seconds']=totals['admission_charged_preparation_seconds']+totals['generation_segment_seconds']
    live_errors=[k for k,v in release['files'].items() if not (FPP_SOURCE/k).is_file() or sha(FPP_SOURCE/k)!=v]
    if fp(release['files'])!=release['identity']:errors.append({'error':'release_fingerprint_mismatch'})
    if live_errors:errors.append({'error':'live_release_files_changed','files':live_errors})
    state=optional(run/'status.json',{});complete=totals['completed']==len(ids) and not state.get('active') and not state.get('preparing')
    return {'run':str(run),'identity':release['identity'],'status':'complete' if complete else 'incomplete','selected_roots':len(ids),'final_acceptance_rate':totals['accepted']/len(ids) if complete else None,'totals':dict(totals),'accepted_reference_input_exposures':dict(backend_counts),'invariant_errors':errors,'per_root':rows,'interpretation':'Same request/token and disjoint time-component accounting as unit. Different corpora and task difficulty do not establish a causal performance comparison.'}

if __name__=='__main__':
    if sys.version_info<(3,11):raise SystemExit('Use Python 3.11+: agent/.venv/bin/python evaluation/scripts/agent/audit_formal.py')
    main()
    audited=read(B/'integration-audit.json')
    if not audited['integrity_checks_passed'] or audited['fpp_same_accounting']['invariant_errors']:
        raise SystemExit('Formal evidence integrity check failed')
