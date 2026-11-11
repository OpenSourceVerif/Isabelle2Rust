"""Independent semantic diagnosis only after exact executed source-test failures."""
from copy import deepcopy
from pathlib import Path
import re,json
from .common import Failure,read,save,digest
from .task_context import fingerprint
from . import source_suite_review as full
from .source_test_context import canonical_mapping,bodyless_interfaces
from .support_scope import needed
from .segmented_context import pages
from .source_failure_check import lock
POLICY='failure-responsibility-independent-source-check-v1'
SYSTEM=full.SYSTEM.replace('the COMPLETE source-test suite before execution','the COMPLETE selected failure responsibility after an actual execution failure').replace('Inspect all actual injected','Inspect all selected actual injected')+' Acceptance means these tests are source-correct, NOT that the candidate passed. Determine premises, helper/observation adaptation and expectations from source. The trigger supplies exact failed test IDs only; observed candidate outputs are intentionally absent. A protected oracle revision must receive a new complete scope judgment before it is executed. Never judge unrelated unprovided test responsibilities.'
SYSTEM+=' Review-only projection may retain exact failed functions and their conservatively resolved helpers/imports/types. Check every projected inventory/obligation; omitted execution tests remain in the original suite and are not part of this judgment. Projection provenance binds original bytes. Never infer whole-suite acceptance from a projected judgment.'
MAX_COMPLETED_PER_RESPONSIBILITY=2

def fail(message,evidence=None):raise Failure('source_check_unresolved',message,evidence)
def failed_ids(frozen,result):
 if result.get('status')!='support_contract_failed' or result.get('compilation',{}).get('status')!='passed':fail('Only executed semantic source-test failure admits this checker')
 found=re.findall(r'^test ([\w:]+)(?: - should panic)? \.\.\. FAILED$',result.get('diagnostic',''),re.M)
 known={r['id'] for r in full.inventory(frozen)}
 if not found or len(found)!=len(set(found)) or set(found)-known:fail('Missing/unknown exact libtest failed IDs; never guess failure scope',{'failed_ids':found,'unknown':sorted(set(found)-known)})
 return sorted(found)
def selection(frozen,failed):
 inv=full.inventory(frozen);byid={r['id']:r for r in inv}
 if not failed or not set(failed)<=byid.keys():fail('Invalid failure test identity')
 selected={(byid[n]['kind'],byid[n]['index']) for n in failed}
 artifacts={('integration',i):code for i,code in enumerate(frozen['tests'])};artifacts.update({('unit',i):r['source'] for i,r in enumerate(frozen.get('unit_tests',[]))})
 # Keep helper-only artifacts and exact cross-artifact references conservatively.
 tested={(r['kind'],r['index']) for r in inv};selected|=set(artifacts)-tested
 changed=True
 while changed:
  code='\n'.join(artifacts[a] for a in sorted(selected));before=set(selected)
  for kind,index in artifacts:
   prefix=f'__i2r_source_contract_{index}' if kind=='integration' else f'__i2r_contract_{index}'
   if re.search(r'\b'+re.escape(prefix)+r'\s*::',code):selected.add((kind,index))
  changed=selected!=before
 tests=[r for r in inv if (r['kind'],r['index']) in selected];names={r['id'] for r in tests}
 obs=[{'id':f'o:{i}','claim':o} for i,o in enumerate(frozen['obligations']) if o.get('test_name') in names]
 sources={o['claim']['source'] for o in obs}
 # Responsibilities explicitly inaccessible/not-applicable for the same source stay visible.
 obs += [{'id':f'o:{i}','claim':o} for i,o in enumerate(frozen['obligations']) if o.get('source') in sources and o.get('disposition') in {'not_applicable','inaccessible'} and f'o:{i}' not in {x['id'] for x in obs}]
 if not obs:fail('Failed test has no explicit source responsibility; unresolved rather than an ungrounded checker')
 return {'policy':POLICY,'failed_test_ids':failed,'artifacts':[{'kind':k,'index':i} for k,i in sorted(selected)],'test_ids':[r['id'] for r in tests],'obligation_ids':[r['id'] for r in obs]},tests,obs

def payload(frozen,state,cfg,failed):
 scope,inv,obs=selection(frozen,failed)
 from .source_failure_projection import build as project
 projected=project(frozen,failed,scope,inv,obs,state);inv=projected['inventory'];obs=projected['obligations']
 projected['projection']['source_page_characters']=cfg['segmented']['source_page_characters']
 scope={**scope,'test_ids':[r['id'] for r in inv],'obligation_ids':[r['id'] for r in obs],'projection':projected['projection']}
 codes=[r['source'] for r in projected['tests']+projected['unit_tests']];tokens=set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*','\n'.join(codes)))
 canonical=canonical_mapping(state);model=state['bundle']['source_model'];referenced={r['source'] for r in canonical if r.get('rust_item','').rsplit('::',1)[-1] in tokens};roots={r['claim']['source'] for r in obs}|referenced;ids=set(needed(model,roots));mapping=[r for r in canonical if r['source'] in ids];api=bodyless_interfaces(state);selected={r.get('rust_item') for r in mapping}|{n for n in api if n.rsplit('::',1)[-1] in tokens}
 changed=True
 while changed:
  text=json.dumps({n:api[n] for n in selected if n in api});extra={n for n,rows in api.items() if any(r['kind'] in {'struct_item','enum_item','type_item','trait_item','impl_item'} for r in rows) and re.search(r'\b'+re.escape(n.rsplit('::',1)[-1])+r'\b',text)};changed=bool(extra-selected);selected|=extra
 # Matching selected API declarations may add concrete type/instance source mappings.
 ids|=set(needed(model,{r['source'] for r in canonical if r.get('rust_item') in selected}));mapping=[r for r in canonical if r['source'] in ids]
 material={'task':'Check every listed test/obligation in this complete failure responsibility, including complete test helpers and expectations. accept means test_correct; test_wrong permits only strictly source-proven protected expectation repair. No candidate output is supplied.','policy':POLICY,'response_protocol':full.PROTOCOL,'failure_scope':scope,'inventory':inv,'tests':projected['tests'],'unit_tests':projected['unit_tests'],'obligations':obs,'source':pages(model,ids,cfg['segmented']['source_page_characters']),'interfaces':{n:api[n] for n in sorted(selected) if n in api},'mapping':mapping,'numeric_policy':state['bundle']['numeric_policy'],'rust_config':state['rust_config'],'framework_and_template_provenance':{k:frozen.get(k) for k in ['test_framework','source_contract_templates','author_group_plan']},'source_hashes':state['bundle'].get('source_hashes'),'source_scope':{'responsibility_roots':sorted(roots),'test_referenced_sources':sorted(referenced),'dependency_closure':sorted(ids),'all_required_source_fields_retained':True}}
 from .expectation_targets import attach
 return attach(frozen,state,material)
def validation_scope(frozen,material,state=None):
 claimed=material.get('failure_scope',{})
 if claimed.get('projection'):
  size=claimed['projection'].get('source_page_characters')
  if state is None or type(size) is not int or size<=0:fail('Projected review lacks its actual state/page-size binding')
  expected=payload(frozen,state,{'segmented':{'source_page_characters':size}},claimed.get('failed_test_ids',[]))
  if expected!=material:fail('Projected review source/API/test/helper/provenance or responsibility bytes changed')
  return {r['id']:r for r in expected['inventory']},{r['id']:r['claim'] for r in expected['obligations']}
 scope,inv,obs=selection(frozen,claimed.get('failed_test_ids',[]))
 if scope!=claimed:fail('Incomplete or changed failure responsibility scope')
 return {r['id']:r for r in inv},{r['id']:r['claim'] for r in obs}
def key_for(material,cfg):
 return fingerprint({'policy':POLICY,'system':SYSTEM,'material':material,'model':{k:cfg['model'].get(k) for k in ['name','endpoint']},'generation':cfg['generation'],'checker_max_output_tokens':full.CHECKER_MAX_OUTPUT_TOKENS,'max_completed_per_responsibility':MAX_COMPLETED_PER_RESPONSIBILITY})

def check(frozen,result,state,cfg,provider,directory,revision=None):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 if cfg['model']['name']!='deepseek-flash':fail('Flash required')
 if revision:
  if revision.get('suite_identity')!=frozen['identity'] or not frozen.get('source_check'):fail('Oracle revision scope lacks protected source-check lineage')
  failed=revision['failed_test_ids']
 else:failed=failed_ids(frozen,result)
 material=payload(frozen,state,cfg,failed);save(directory/'mapping-provenance'/(fingerprint(state['mapping'])+'.json'),state['mapping']);key=key_for(material,cfg);responsibility_scope=selection(frozen,failed)[0];responsibility=fingerprint({'artifacts':responsibility_scope['artifacts'],'tests':responsibility_scope['test_ids'],'obligations':responsibility_scope['obligation_ids']})
 save(directory/'failures'/(fingerprint([lock(state),result,frozen['identity']])+'.json'),{'failure':result,'candidate_lock':lock(state),'suite_identity':frozen['identity'],'revision':revision,'not_checker_input':True})
 lp=directory/'ledger.json';ledger=read(lp) if lp.exists() else {'policy':POLICY,'attempts':[]}
 if ledger.get('policy')!=POLICY:fail('Failure-check policy changed without explicit migration')
 completed=[r for r in ledger['attempts'] if r['status']=='completed'];cached=next((r for r in completed if r['scope']==key),None)
 if cached:
  row=cached;path=Path(row['directory']);proposal=read(path/'verdict.json');full.verify_receipt(row['provider_receipt'])
  if read(path/'input.json')!=material:fail('Cached failure scope input bytes changed')
  if digest(path/'verdict.json')!=row['verdict_sha256']:fail('Cached failure judgment bytes changed')
 else:
  if sum(r.get('responsibility')==responsibility for r in completed)>=MAX_COMPLETED_PER_RESPONSIBILITY:fail('Two completed judgments exhausted for this failure responsibility')
  path=directory/f'judgment-{len(ledger["attempts"])+1:03d}';path.mkdir();save(path/'input.json',material);save(path/'original-suite.json',frozen);row={'scope':key,'responsibility':responsibility,'directory':str(path),'status':'reserved'};ledger['attempts'].append(row);save(lp,ledger)
  proposal=full.call_record(provider,cfg,SYSTEM,material,path,row,ledger,lp)
 verdict,proof=full.resolve_citations(proposal,material,frozen,state,cfg,provider,path,row,ledger,lp)
 evidence={'scope':key,'status':'test_correct' if verdict['action']=='accept' else verdict['action'],'cache_hit':cached is not None,'evidence':str(path),'failed_test_ids':failed,'responsibility':responsibility,'verdict_sha256':digest(path/'validated-verdict.json'),'provider_receipt':row['provider_receipt']}
 if verdict['action']=='accept':return {'action':'accept_revision' if revision else 'candidate_repair','source_check':evidence,'evidence':str(path)}
 if verdict['action']=='needs_revision':
  if revision or sum(r.get('responsibility')==responsibility for r in completed)>=MAX_COMPLETED_PER_RESPONSIBILITY:fail('No further pattern revision after the final permitted independent judgment',evidence)
  from .source_pattern_revision import propose
  updated=propose(frozen,verdict,state,material,cfg,provider,path/'pattern-repair',result)
 elif verdict['action']=='test_wrong':updated=full.revise(frozen,verdict,state,material)
 else:fail('Failure source semantics remain unresolved; preserve tests and stop',evidence)
 save(path/'diagnosis.json',updated['source_check']);updated['binding_audit']={'method':'source-pattern-check-v1' if verdict['action']=='needs_revision' else 'source-expectation-check-v1','path':str(path),'second_model_review':True}
 return {'action':'binding_fix','frozen':updated,'source_check':evidence,'evidence':str(path),'revision_review':{'suite_identity':updated['identity'],'failed_test_ids':failed,'origin_evidence':str(path),'original_failure':result}}

def require_revision(frozen,state,cfg,accepted):
 if not isinstance(accepted,dict):fail('Protected revised oracle lacks complete current judgment')
 record=accepted.get('source_check',{});revision=accepted.get('revision',{});material=payload(frozen,state,cfg,revision.get('failed_test_ids',[]));path=Path(record.get('evidence',''))
 if record.get('status')!='test_correct' or record.get('scope')!=key_for(material,cfg):fail('Protected revised oracle scope changed; independent recheck required')
 full.verify_receipt(record.get('provider_receipt'))
 if not (path/'validated-verdict.json').is_file() or digest(path/'validated-verdict.json')!=record.get('verdict_sha256') or read(path/'input.json')!=material:fail('Protected revised oracle acceptance evidence changed')
 proposal=read(path/'validated-verdict.json');full.validate(proposal,frozen,state,material)
 if proposal.get('action')!='accept':fail('Protected revised oracle was not accepted')
 return record

def require_state(state,cfg,work):
 from .support_issue_lineage import binding
 from .segmented_support import passed_test_names
 result=state.get('support_evidence',{});fid=result.get('frozen_identity');path=Path(work)/'support-tests'/(str(fid)+'.json')
 if not path.is_file() or result.get('status')!='passed' or state.get('support_pass_candidate')!=lock(state):fail('Current candidate lacks complete actual source execution')
 frozen=read(path)
 if frozen.get('source_check'):require_revision(frozen,state,cfg,state.get('source_oracle_revision_accepted'))
 inv={r['id'] for r in full.inventory(frozen)}
 if result.get('execution_binding')!=binding(state,frozen) or result.get('missing_required_tests')!=[] or result.get('immutable_test_sources')!=frozen['tests'] or result.get('immutable_unit_tests')!=frozen.get('unit_tests',[]) or result.get('obligations')!=frozen['obligations']:fail('Source execution identity/coverage differs')
 if state.get('source_oracle_revision_review'):fail('Protected oracle revision still needs independent checking')
 for rec in [result.get('compilation',{}),result.get('record',{})]:
  if rec.get('status')!='passed' or rec.get('returncode')!=0:fail('Source suite lacks successful compile/execution receipts')
 rec=result['record'];paths=[rec.get('stdout'),rec.get('stderr')]
 if '--format=pretty' not in rec.get('command',[]) or any(not p or not Path(p).is_file() or digest(p)!=result.get('execution_artifacts',{}).get(str(Path(p))) for p in paths):fail('Source execution artifact changed')
 if not inv<=passed_test_names(''.join(Path(p).read_text() for p in paths)):fail('Not every declared source test actually passed')
 return {'status':'passed','policy':POLICY,'routine_semantic_review_required':False,'frozen_identity':fid}
