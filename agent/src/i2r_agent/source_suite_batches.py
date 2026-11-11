"""Length-only, complete-artifact source-check fallback; every request is charged."""
import json,re
from copy import deepcopy
from pathlib import Path
from .common import Failure,read,save,digest
from .task_context import fingerprint
from .segmented_context import pages
from .support_scope import needed
POLICY='length-only-complete-artifact-responsibility-union-v1'
SYSTEM='''This request owns one batch of a complete source-test semantic check after an actual output-length failure. Check every owned test and obligation in check_scope, and return exactly those checklist IDs. The fixed full_suite_responsibilities index establishes the complete responsibility union, not additional tests to judge in this response. Each supplied artifact includes its full original test/helper code with original global indices. Other batches have separate isolated judgments. Inspect all assertions, inputs and shared helpers within these artifacts using the supplied exact source dependency closure and bodyless interfaces. Do not infer an unprovided source fact. Return brief complete records: reuse exact evidence IDs; use short source excerpts and concise premise/expectation/assertion/reason fields. Do not repeat source text in prose. An accept needs every owned item; uncertainty or a source defect must be reported honestly. No candidate edits or oracle weakening.'''

def fail(message,evidence=None):raise Failure('source_suite_review_unresolved',message,evidence)

def plan(frozen):
 from .source_suite_review import inventory
 inv=inventory(frozen);groups=frozen.get('author_group_plan',{}).get('groups',[])
 if len(groups)<2:fail('Length fallback requires at least two existing source responsibility groups; no arbitrary test split')
 owner={s:i for i,g in enumerate(groups) for s in g}
 if sum(map(len,groups))!=len(owner):fail('Source responsibility groups overlap')
 parent=list(range(len(groups)))
 def root(i):
  while parent[i]!=i:i=parent[i]
  return i
 def join(ids):
  ids=list(ids)
  for i in ids[1:]:parent[root(i)]=root(ids[0])
 artifacts={(r['kind'],r['index']) for r in inv};test={r['id']:r for r in inv};artifact_owners={a:set() for a in artifacts};obligation_owners={}
 for i,o in enumerate(frozen['obligations']):
  name=o.get('test_name');g=owner.get(o.get('source'))
  if name in test:
   a=(test[name]['kind'],test[name]['index']);artifact_owners[a].update([g] if g is not None else range(len(groups)));obligation_owners[f'o:{i}']=('artifact',a)
  elif o.get('disposition') in {'not_applicable','inaccessible'} and g is not None:obligation_owners[f'o:{i}']=('group',g)
  else:fail('Cannot assign every obligation to an exact test artifact or explicit source disposition',{'id':f'o:{i}','claim':o})
 for a,ids in artifact_owners.items():
  if not ids:fail('A test artifact has no source-bound obligation ownership',a)
  join(ids)
 rows={}
 for i in range(len(groups)):rows.setdefault(root(i),{'source_groups':[],'owned_sources':[],'artifacts':[],'test_ids':[],'obligation_ids':[]})['source_groups'].append(i);rows[root(i)]['owned_sources']+=groups[i]
 for a,ids in artifact_owners.items():rows[root(next(iter(ids)))]['artifacts'].append({'kind':a[0],'index':a[1]})
 for t in inv:rows[root(next(iter(artifact_owners[(t['kind'],t['index'])])))]['test_ids'].append(t['id'])
 for oid,(kind,x) in obligation_owners.items():rows[root(x if kind=='group' else next(iter(artifact_owners[x])))]['obligation_ids'].append(oid)
 result=[]
 for row in rows.values():
  if not row['test_ids'] and not row['obligation_ids']:continue
  row['id']=f'b:{len(result)}';row['artifacts']=sorted(row['artifacts'],key=lambda x:(x['kind'],x['index']));row['owned_sources']=sorted(row['owned_sources']);result.append(row)
 if len(result)<2:fail('Whole artifacts share responsibilities; no safe multi-batch fallback exists')
 validate_union(result,inv,frozen['obligations'])
 all_artifacts={('integration',i) for i in range(len(frozen['tests']))}|{('unit',i) for i in range(len(frozen.get('unit_tests',[])))}
 common_artifacts=[{'kind':kind,'index':index} for kind,index in sorted(all_artifacts-artifacts)]
 return {'policy':POLICY,'common_artifacts':common_artifacts,'batches':result,'full_test_ids':[r['id'] for r in inv],'full_obligation_ids':[f'o:{i}' for i in range(len(frozen['obligations']))]}

def validate_union(rows,inv,obligations):
 for key,expected in [('test_ids',[r['id'] for r in inv]),('obligation_ids',[f'o:{i}' for i in range(len(obligations))])]:
  actual=[n for r in rows for n in r[key]]
  if len(actual)!=len(set(actual)) or set(actual)!=set(expected):fail('Batch responsibilities must form an exact nonoverlapping complete union',{'field':key,'expected':expected,'actual':actual})

def material(frozen,state,cfg,p,batch):
 from .source_suite_review import payload
 full=payload(frozen,state,cfg);scope={'policy':POLICY,'batch_id':batch['id'],'plan_identity':fingerprint(p),'test_ids':batch['test_ids'],'obligation_ids':batch['obligation_ids']}
 artifacts=batch['artifacts']+p['common_artifacts'];owned_o={int(n.split(':')[1]) for n in batch['obligation_ids']};model=state['bundle']['source_model'];ids=needed(model,set(batch['owned_sources'])|{frozen['obligations'][i]['source'] for i in owned_o})
 # Concrete test instances may use shared source types beyond a function's generic type variables. Retain all supplied type/class facts and their dependency closure in every batch.
 common={p['source'] for p in full['source'] if p['source'].startswith(('type:','class:'))}
 codes=[frozen['tests'][a['index']] if a['kind']=='integration' else frozen['unit_tests'][a['index']]['source'] for a in artifacts]
 tokens=set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*','\n'.join(codes)))
 # Conservative lexical use of exact mechanical Rust item leaves retains shared
 # helper/instance source facts even when they are not an owned obligation.
 referenced={r['source'] for r in full['mapping'] if r.get('rust_item','').rsplit('::',1)[-1] in tokens}
 ids=set(ids)|set(needed(model,common|referenced))
 full['shared_source_type_class_ids']=sorted(common);full['artifact_referenced_sources']=sorted(referenced)
 full.update(task='Check exactly this batch of the full suite. Complete all owned checklist records; the complete-suite acceptance requires every batch.',check_scope=scope,full_suite_responsibilities={'plan':p,'inventory':full['inventory'],'obligations':[{'id':o['id'],'source':o['claim']['source'],'test_name':o['claim'].get('test_name'),'disposition':o['claim'].get('disposition')} for o in full['obligations']]},inventory=[r for r in full['inventory'] if r['id'] in batch['test_ids']],obligations=[r for r in full['obligations'] if r['id'] in batch['obligation_ids']],source=pages(model,ids,cfg['segmented']['source_page_characters']))
 full['tests']=[{'index':a['index'],'source':frozen['tests'][a['index']]} for a in artifacts if a['kind']=='integration']
 full['unit_tests']=[{'index':a['index'],**frozen['unit_tests'][a['index']]} for a in artifacts if a['kind']=='unit']
 from .expectation_targets import attach
 return attach(frozen,state,full)

def validation_scope(frozen,material):
 from .source_suite_review import inventory
 p=plan(frozen);claimed=material.get('check_scope',{});batch=next((b for b in p['batches'] if b['id']==claimed.get('batch_id')),None)
 if batch is None or claimed!={'policy':POLICY,'batch_id':batch['id'],'plan_identity':fingerprint(p),'test_ids':batch['test_ids'],'obligation_ids':batch['obligation_ids']}:fail('Invalid or incomplete batch scope')
 inv={r['id']:r for r in inventory(frozen) if r['id'] in batch['test_ids']};obs={f'o:{i}':o for i,o in enumerate(frozen['obligations']) if f'o:{i}' in batch['obligation_ids']}
 return inv,obs

def length_trigger(row,key):
 if row.get('scope')!=key and row.get('admitted_length_scope')!=key:return False
 e=row.get('error',{});v=e.get('evidence') or {}
 if row.get('status')!='unresolved_response' or e.get('code')!='incomplete_response' or v.get('finish_reason')!='length':return False
 response=Path(v.get('response',''));request=response.with_name('request.json');call=response.with_name('call-state.json')
 if not all(x.is_file() for x in [request,response,call]):fail('Length fallback needs actual request/response/phase archives')
 r=read(response)
 if read(request).get('model')!='deepseek-flash' or read(call).get('phase')!='source_test_check' or r['choices'][0].get('finish_reason')!='length':fail('Length fallback trigger is not an actual Flash checker truncation')
 return {'original_scope':row['scope'],'response':str(response),'response_sha256':digest(response),'request':str(request),'request_sha256':digest(request),'call_state':str(call),'call_state_sha256':digest(call),'input':str(Path(row['directory'])/'input.json'),'input_sha256':digest(Path(row['directory'])/'input.json'),'partial_never_accepted':True}

def admit_legacy_length(row,frozen,state,cfg):
 """Explicit external migration only; exact semantic payload equality required."""
 from . import source_suite_review as review
 old=read(Path(row['directory'])/'input.json');new=review.payload(frozen,state,cfg)
 if {k:v for k,v in old.items() if k!='policy'}!={k:v for k,v in new.items() if k!='policy'}:fail('Legacy truncated request differs from current complete checker scope; no length admission')
 migrated=deepcopy(row);migrated['admitted_length_scope']=review.scope(frozen,state,cfg)
 proof=length_trigger(migrated,migrated['admitted_length_scope'])
 if not proof:fail('Only an actual unresolved length response may migrate')
 migrated['length_scope_migration']={'from_policy':old['policy'],'to_policy':new['policy'],'original_scope':row['scope'],'new_scope':migrated['admitted_length_scope'],'original_input_sha256':fingerprint(old),'new_input_sha256':fingerprint(new),'semantic_payload_unchanged':True,'partial_accepted':False,'trigger':proof}
 return migrated

def run(frozen,state,cfg,provider,directory,key,ledger,trigger=None):
 from . import source_suite_review as review
 directory=Path(directory);ledger_path=directory/'ledger.json';p=plan(frozen)
 rounds=[r for r in ledger['attempts'] if r.get('kind')=='batch_round' and r['scope']==key]
 if len(rounds)>1:fail('Duplicate fallback round for one exact scope')
 if rounds:row=rounds[0]
 else:
  if not trigger:fail('No actual length trigger for batch fallback')
  if sum(r.get('status')=='completed' for r in ledger['attempts'])>=review.MAX_COMPLETED:fail('Two complete checker rounds exhausted')
  path=directory/f'batch-round-{len(ledger["attempts"])+1:03d}';path.mkdir();row={'kind':'batch_round','scope':key,'suite_identity':frozen['identity'],'directory':str(path),'status':'reserved','plan':p,'plan_identity':fingerprint(p),'trigger':trigger,'batches':[]};ledger['attempts'].append(row);save(ledger_path,ledger);save(path/'original-suite.json',frozen)
 if row['plan']!=p or row['plan_identity']!=fingerprint(p):fail('Fallback responsibility plan changed')
 if row['status']=='unresolved_round':fail('A batch did not accept; preserve failure without another fallback loop',row.get('failure'))
 path=Path(row['directory']);was_complete=row['status']=='completed'
 if was_complete:
  evidence=record(row,p,True);require(frozen,state,cfg,evidence);return evidence
 for batch in p['batches']:
  records=[r for r in row['batches'] if r['batch_id']==batch['id']]
  if len(records)>1:fail('Duplicate batch judgment')
  child=records[0] if records else None;request=material(frozen,state,cfg,p,batch)
  if child and child.get('status')=='completed':
   bp=Path(child['directory']);proposal=read(bp/'verdict.json')
   if digest(bp/'verdict.json')!=child['verdict_sha256'] or read(bp/'input.json')!=request:fail('Completed batch artifacts changed')
   review.verify_receipt(child['provider_receipt'])
  else:
   if was_complete:fail('Aggregate accepted without a completed batch')
   bp=path/(batch['id'].replace(':','-'))
   if child is None:child={'batch_id':batch['id'],'directory':str(bp),'status':'reserved','scope':key,'request_identity':fingerprint(request)};row['batches'].append(child)
   bp.mkdir(exist_ok=True);save(bp/'input.json',request);save(ledger_path,ledger)
   try:proposal=review.call_record(provider,cfg,review.SYSTEM+' '+SYSTEM,request,bp,child,ledger,ledger_path)
   except Failure as error:
    if error.code not in {'provider_error','provider_protocol_error','budget_exhausted'}:row.update(status='unresolved_round',failure={'batch_id':batch['id'],'code':error.code,'message':str(error)});save(ledger_path,ledger)
    raise
  try:
   normalized,proof=review.resolve_citations(proposal,request,frozen,state,cfg,provider,bp,child,ledger,ledger_path)
   child['citation_proof_sha256']=digest(bp/'citation-verification.json');save(ledger_path,ledger)
   if normalized.get('action')!='accept':fail('Batch did not accept; protected broad revisions are not inferred or applied',{'batch_id':batch['id'],'action':normalized.get('action')})
  except Failure as error:
   if error.code not in {'provider_error','provider_protocol_error','budget_exhausted'}:row.update(status='unresolved_round',failure={'batch_id':batch['id'],'code':error.code,'message':str(error)});save(ledger_path,ledger)
   raise
 aggregate={'action':'accept','scope':key,'plan_identity':fingerprint(p),'tests':p['full_test_ids'],'obligations':p['full_obligation_ids'],'batches':[{'batch_id':b['batch_id'],'verdict_sha256':b['resolved_verdict_sha256'],'original_verdict_sha256':b['verdict_sha256'],'citation_proof_sha256':b['citation_proof_sha256'],'provider_receipt':b['provider_receipt'],'directory':b['directory']} for b in row['batches']],'model_judgments':len(row['batches']),'complete_suite_check_rounds':1}
 save(path/'aggregate.json',aggregate);row.update(status='completed',action='accept',aggregate_sha256=digest(path/'aggregate.json'));save(ledger_path,ledger)
 evidence=record(row,p,False)
 require(frozen,state,cfg,evidence);return evidence

def record(row,p,cached):
 from . import source_suite_review as review
 return {'action':'accept','status':'accepted','method':POLICY,'policy':review.POLICY,'scope':row['scope'],'suite_identity':row['suite_identity'],'evidence':row['directory'],'ledger':str(Path(row['directory']).parent/'ledger.json'),'aggregate_sha256':row['aggregate_sha256'],'complete_tests':len(p['full_test_ids']),'complete_obligations':len(p['full_obligation_ids']),'model_judgments':len(row['batches']),'complete_suite_check_rounds':1,'cache_hit':cached}

def require(frozen,state,cfg,evidence):
 from . import source_suite_review as review
 key=review.scope(frozen,state,cfg);p=plan(frozen);path=Path(evidence.get('evidence',''));ledger=read(Path(evidence['ledger']));rows=[r for r in ledger['attempts'] if r.get('kind')=='batch_round' and r.get('scope')==key and r.get('status')=='completed']
 if len(rows)!=1 or evidence.get('scope')!=key or evidence.get('status')!='accepted':fail('Missing current complete batch round')
 row=rows[0]
 if row['plan']!=p or row['plan_identity']!=fingerprint(p) or row.get('action')!='accept' or row['aggregate_sha256']!=evidence.get('aggregate_sha256') or digest(path/'aggregate.json')!=row['aggregate_sha256']:fail('Aggregate checker evidence changed')
 if len(row['batches'])!=len(p['batches']) or {b['batch_id'] for b in row['batches']}!={b['id'] for b in p['batches']}:fail('Missing/duplicate batch in complete acceptance')
 aggregate=read(path/'aggregate.json')
 if aggregate['tests']!=p['full_test_ids'] or aggregate['obligations']!=p['full_obligation_ids'] or aggregate['plan_identity']!=fingerprint(p):fail('Aggregate responsibility manifest changed')
 actual_tests=[];actual_obs=[]
 for batch in p['batches']:
  child=next(b for b in row['batches'] if b['batch_id']==batch['id']);bp=Path(child['directory']);m=material(frozen,state,cfg,p,batch)
  if child.get('status')!='completed' or child.get('action')!='accept' or read(bp/'input.json')!=m or digest(bp/'verdict.json')!=child.get('verdict_sha256') or digest(bp/'validated-verdict.json')!=child.get('resolved_verdict_sha256'):fail('Invalid completed batch receipt')
  binding={'batch_id':child['batch_id'],'verdict_sha256':child['resolved_verdict_sha256'],'original_verdict_sha256':child['verdict_sha256'],'citation_proof_sha256':child['citation_proof_sha256'],'provider_receipt':child['provider_receipt'],'directory':child['directory']}
  if binding not in aggregate['batches'] or digest(bp/'citation-verification.json')!=child['citation_proof_sha256']:fail('Batch receipt/proof differs from the accepted aggregate')
  review.verify_receipt(child['provider_receipt']);original=read(bp/'verdict.json');v=read(bp/'validated-verdict.json')
  if any(v.get(k)!=original.get(k) for k in original if k!='source_evidence'):fail('Batch semantic verdict changed during citation repair')
  checks=review.validate(v,frozen,state,m)
  if v.get('action')!='accept':fail('Nonaccepted batch cannot contribute coverage')
  actual_tests+=list(checks['tests']);actual_obs+=list(checks['obligations'])
  proof=read(bp/'citation-verification.json')
  if proof.get('protocol_receipt'):review.verify_receipt(proof['protocol_receipt'])
 if len(actual_tests)!=len(set(actual_tests)) or set(actual_tests)!=set(p['full_test_ids']) or len(actual_obs)!=len(set(actual_obs)) or set(actual_obs)!=set(p['full_obligation_ids']):fail('Actual batch verdicts do not cover the whole suite exactly')
 return evidence
