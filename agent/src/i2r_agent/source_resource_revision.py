"""One source-justified numeric resource resampling, separate from oracle edits.

Only numeric literal leaves in exact failed test functions may change. All calls,
assertions, helpers and obligation identities remain; independent recheck and full
source/differential execution are mandatory before acceptance.
"""
from copy import deepcopy
from pathlib import Path
import re,time
from .common import Failure,read,save,digest
from .task_context import Conversation,fingerprint
from . import source_suite_review as full
from .source_pattern_revision import parser,target_function,repair_receipt,verify_repair_receipt
from .source_resources import bound

POLICY='source-proven-resource-resampling-v1'
SYSTEM='Propose numeric literals for an independently source-confirmed resource-infeasible test. Candidate bodies and observed outputs are withheld. Preserve the source algorithm, all calls, helpers, assertion operators/counts, tests and obligations. Distinguish large data from recursion/iteration/enumeration/output controls. Keep feasible arbitrary large-data coverage; do not replace it with small-only tests. Independently derive every changed input/expected pair from source equations. Only supplied numeric literal slots may change. If this cannot retain every responsibility, return unresolved. This proposal is not acceptance: a new independent source judgment and complete source/D execution follow.'
ASSESSMENT={'tests':[{'test_id':'exact executed failed ID','control_parameters':['source parameter controlling steps/depth/output'],
 'data_parameters':['source data parameter, if any'],'growth':'source-derived work/output growth for the actual input',
 'feasible_plan':'same responsibilities with feasible controls; retain feasible large data or explain why no such example exists',
 'basis':['exact existing source evidence ID']}]}


def fail(message,evidence=None):raise Failure('source_check_unresolved',message,evidence)


def numeric_literal(text,kind):
    if kind=='string_literal':return bool(re.fullmatch(r'"-?[0-9]+"',text))
    return kind=='integer_literal' and bool(re.fullmatch(r'[0-9][0-9_]*(?:[ui](?:8|16|32|64|128|size))?',text))


def slots(frozen,test):
    # Standalone integration test functions only. Unit/higher-level restructuring
    # needs a separate policy, never inferred from a crash.
    code,function,start=target_function(frozen,test);data=function.encode();root=parser().parse(data).root_node
    if root.has_error:fail('Resource test is not parseable')
    todo=[root];leaves=[]
    while todo:
        node=todo.pop()
        if numeric_literal(node.text.decode(),node.type):leaves.append(node)
        else:todo.extend(node.named_children)
    result=[]
    for n in sorted(leaves,key=lambda n:n.start_byte):
        result.append({'id':fingerprint([frozen['identity'],test['id'],start+n.start_byte,start+n.end_byte,n.text.decode()]),
          'test_id':test['id'],'kind':n.type,'old':n.text.decode(),'start':start+n.start_byte,'end':start+n.end_byte,'index':test['index']})
    return result


def eligibility(frozen,verdict,state,material,failure):
    checks=full.validate(verdict,frozen,state,material)
    resource=bound(frozen,failure)
    if frozen.get('resource_revision_origin'):fail('One resource resampling already used for this suite lineage')
    if not resource or not resource['scope_bound'] or verdict.get('action')!='needs_revision':fail('Resource resampling requires a bound execution failure and independent needs_revision judgment')
    if any(r['verdict']=='uncertain' for group in checks.values() for r in group.values()):fail('Uncertain source evidence cannot authorize resampling')
    assessment=verdict.get('resource_assessment');entries=assessment.get('tests') if isinstance(assessment,dict) else None
    if not isinstance(entries,list) or not entries:fail('Missing explicit source resource assessment')
    wrong={name for name,row in checks['tests'].items() if row['verdict']=='wrong'}
    if not wrong or {r.get('test_id') for r in entries if isinstance(r,dict)}!=wrong or len(entries)!=len(wrong) or not wrong<=set(resource['failed_test_ids']):fail('Resource assessment must exactly cover all independently wrong, executed tests')
    inv={r['id']:r for r in full.inventory(frozen)};sources={r['id'] for r in verdict['source_evidence'] if r['kind']=='source'};allowed={}
    for row in entries:
        name=row['test_id']
        if set(row)!={'test_id','control_parameters','data_parameters','growth','feasible_plan','basis'}:fail('Incomplete resource assessment schema')
        for field in ['control_parameters','data_parameters']:
            if not isinstance(row[field],list) or any(not isinstance(v,str) or not v.strip() for v in row[field]):fail('Resource parameters must identify source roles')
        if not row['control_parameters'] or any(not isinstance(row[k],str) or not row[k].strip() for k in ['growth','feasible_plan']):fail('Source work/output growth and feasible plan are required')
        if not isinstance(row['basis'],list) or not row['basis'] or not set(row['basis'])<=set(checks['tests'][name]['basis']) or not set(row['basis'])&sources:fail('Source evidence, not API shape or runtime failure, must justify resampling')
        for slot in slots(frozen,inv[name]):allowed[slot['id']]=slot
    if not allowed:fail('No supported numeric literal slots; do not restructure tests')
    return checks,resource,allowed


def apply(frozen,verdict,proposal,state,material,failure):
    checks,resource,allowed=eligibility(frozen,verdict,state,material,failure)
    if isinstance(proposal,dict) and proposal.get('action')=='unresolved':
        raise Failure('source_check_unresolved','Resource resampling explicitly unresolved; original tests retained',
            {'action':'unresolved','reason':proposal.get('reason'),'derivation':proposal.get('derivation'),'policy':POLICY})
    if not isinstance(proposal,dict) or set(proposal)-{'action','derivation','literal_edits','obligation_edits'} or proposal.get('action')!='resample_resource_literals' or not isinstance(proposal.get('derivation'),str) or not proposal['derivation'].strip():fail('Invalid bounded resource proposal')
    edits=proposal.get('literal_edits');prose=proposal.get('obligation_edits',[])
    if not isinstance(edits,list) or not edits or not isinstance(prose,list):fail('Explicit literal edits required')
    updated=deepcopy(frozen);replacements={};seen=set();changed=set()
    for edit in edits:
        if not isinstance(edit,dict) or set(edit)!={'slot_id','old','new'}:fail('Only exact literal slots may change')
        slot=allowed.get(edit['slot_id'])
        if not slot or slot['id'] in seen or edit['old']!=slot['old'] or not isinstance(edit['new'],str) or not numeric_literal(edit['new'],slot['kind']):fail('Unknown/duplicate/nonliteral resource edit')
        # Keep primitive suffixes: changing a type is not resampling a value.
        if slot['kind']=='integer_literal' and re.sub(r'^[0-9_]+','',edit['old'])!=re.sub(r'^[0-9_]+','',edit['new']):fail('Numeric type suffix must stay fixed')
        if edit['new']==edit['old']:fail('Resource proposal made no change')
        seen.add(slot['id']);changed.add(slot['test_id']);replacements.setdefault(slot['index'],[]).append((slot,edit['new']))
    if changed!={name for name,row in checks['tests'].items() if row['verdict']=='wrong'}:fail('Every wrong resource test must be addressed')
    for index,rows in replacements.items():
        data=frozen['tests'][index].encode()
        for slot,new in sorted(rows,key=lambda pair:pair[0]['start'],reverse=True):data=data[:slot['start']]+new.encode()+data[slot['end']:]
        updated['tests'][index]=data.decode()
        if parser().parse(data).root_node.has_error:fail('Changed test is not parseable')
    # Only case/expected prose for the same changed test can be refreshed. All
    # source/category/disposition/test_name identities and sibling obligations stay.
    seen_obs=set()
    for edit in prose:
        if not isinstance(edit,dict) or set(edit)!={'id','field','old','new'} or edit['field'] not in {'case','expected_basis'}:fail('Only changed resource example prose may change')
        oid=edit['id'];field=edit['field'];key=(oid,field)
        if oid not in checks['obligations'] or key in seen_obs:fail('Unknown/duplicate resource obligation')
        index=int(oid.split(':')[1]);claim=frozen['obligations'][index]
        if claim.get('test_name') not in changed or claim.get(field)!=edit['old'] or not isinstance(edit['new'],str) or not edit['new'].strip():fail('Unrelated obligation or empty justification')
        seen_obs.add(key);updated['obligations'][index][field]=edit['new']
    if full.inventory(updated)!=full.inventory(frozen):fail('Resource correction changed test inventory')
    updated.update(parent_identity=frozen['identity'],oracle_identity=frozen.get('oracle_identity',frozen['identity']),
      resource_revision_origin=resource,status='resource_resampling_pending_independent_check',
      source_check={'policy':POLICY,'original_judgment':deepcopy(verdict),'model_patch':deepcopy(proposal),
                    'requires_new_scope_acceptance':True,'changed_test_ids':sorted(changed)})
    updated['identity']=fingerprint({'parent':frozen['identity'],'tests':updated['tests'],'unit_tests':updated.get('unit_tests',[]),
      'obligations':updated['obligations'],'source_check':updated['source_check'],'resource_origin':resource})
    return updated


def propose(frozen,verdict,state,material,cfg,provider,directory,failure):
    _,resource,allowed=eligibility(frozen,verdict,state,material,failure)
    request={'task':SYSTEM,'schema':{'action':'resample_resource_literals','derivation':'source-derived changed input/expected pairs and work bound',
       'literal_edits':[{'slot_id':'exact permitted ID','old':'exact numeric literal token','new':'same-kind numeric literal token'}],
       'obligation_edits':[{'id':'o:index','field':'case | expected_basis','old':'complete original prose','new':'same responsibility, source-derived new example'}]},
       'independent_judgment':verdict,'resource_failure':resource,'source':material['source'],'interfaces':material['interfaces'],
       'numeric_policy':material['numeric_policy'],'native_numeric_contracts':material.get('native_numeric_contracts'),'tests':material['tests'],'unit_tests':material['unit_tests'],'obligations':material['obligations'],
       'literal_slots':[{k:v for k,v in row.items() if k not in {'start','end'}} for row in allowed.values()]}
    key=fingerprint({'policy':POLICY,'request':request,'model':cfg['model'],'generation':cfg['generation']});path=Path(directory)/key;path.mkdir(parents=True,exist_ok=True);rp=path/'record.json'
    if rp.exists():
        record=read(rp)
        if record.get('status')!='completed':fail('Resource proposal already attempted; no unbounded retry')
        verify_repair_receipt(record['provider_receipt'])
        if read(path/'input.json')!=request or digest(path/'proposal.json')!=record['proposal_sha256']:fail('Resource proposal scope changed')
        proposal=read(path/'proposal.json')
    else:
        record={'policy':POLICY,'status':'reserved','not_semantic_judgment':True};save(rp,record);save(path/'input.json',request)
        before=provider.calls;started=time.monotonic()
        try:
            conversation=Conversation(path/'conversation.json',cfg);conversation.enter('source-resource-resampling')
            proposal=conversation.call(provider,SYSTEM,request,path/'request',phase='source_test_repair')
            save(path/'proposal.json',proposal);record.update(status='completed',proposal_sha256=digest(path/'proposal.json'),provider_receipt=repair_receipt(provider))
        finally:
            record['calls']=provider.calls-before;record['seconds']=time.monotonic()-started;save(rp,record)
    updated=apply(frozen,verdict,proposal,state,material,failure)
    updated['source_check'].update(patch_provider_receipt=record['provider_receipt'],patch_path=str(path))
    save(path/'protected-revision.json',updated);return updated
