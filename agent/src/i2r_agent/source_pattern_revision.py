"""Narrow model-proposed correction of a proven wrong Result error pattern.

Only pattern bytes change. Actual calls/inputs, helpers, other assertions and
responsibility identities remain fixed; a fresh independent judgment is mandatory.
"""
from copy import deepcopy
from pathlib import Path
import re,time
from .common import Failure,read,save,digest
from .task_context import Conversation,fingerprint
from . import source_suite_review as full
from .segmented_contract import items,interfaces

POLICY='source-proven-result-pattern-revision-v1'
SYSTEM='You are a restricted source-test patch proposer, not an independent semantic checker and not a candidate repairer. Use the supplied completed independent wrong-test judgment and its exact source evidence. No candidate bodies, execution outputs or generation history are supplied. Never change actual calls/inputs, helpers, test IDs, other assertions or responsibility identities. Propose only the allowed exact Result pattern correction and optional narrowly localized stale oracle prose corrections. A separate independent check must accept the changed scope before tests execute. If the narrow operation is insufficient, return unresolved. Do not delete cases or reduce obligations.'

def fail(message,evidence=None):raise Failure('source_check_unresolved',message,evidence)
def parser():
 from tree_sitter import Language,Parser
 import tree_sitter_rust
 return Parser(Language(tree_sitter_rust.language()))
def pattern_spans(code):
 data=code.encode();root=parser().parse(data).root_node
 if root.has_error:return []
 result=[];todo=[root]
 while todo:
  node=todo.pop();todo.extend(node.children)
  if node.type!='macro_invocation' or data[node.child_by_field_name('macro').start_byte:node.child_by_field_name('macro').end_byte]!=b'assert':continue
  body=next((n for n in node.children if n.type=='token_tree'),None)
  if body is None:continue
  nested=[n for n in body.named_children if n.type=='token_tree']
  if len(nested)!=1:continue
  inner=nested[0]
  if data[body.start_byte+1:inner.start_byte].strip()!=b'matches!' or data[inner.end_byte:body.end_byte-1].strip():continue
  commas=[n for n in inner.children if n.type==',']
  if len(commas) not in {1,2}:continue
  end=commas[1].start_byte if len(commas)==2 else inner.end_byte-1
  if len(commas)==2 and data[commas[1].end_byte:inner.end_byte-1].strip():continue
  actual=data[inner.start_byte+1:commas[0].start_byte].decode().strip()
  raw=data[commas[0].end_byte:end];a=commas[0].end_byte+len(raw)-len(raw.lstrip());b=commas[0].end_byte+len(raw.rstrip())
  pattern=data[a:b].decode()
  # No wildcard, OR pattern, guard or nested adapter accepted by this rule.
  if re.fullmatch(r'(?:Err|::(?:core|std)::result::Result::Err)\s*\(\s*(?:[A-Za-z_]\w*::)+[A-Za-z_]\w*\s*\)',pattern):
   result.append({'start':a,'end':b,'actual':actual,'old_pattern':pattern})
 return result

def standard_constructor_scope(code,state):
 # This operation only supports compiled standalone integration tests with the
 # standard prelude. Reject any possible constructor/module macro shadowing.
 if any(n.rsplit('::',1)[-1] in {'Ok','Err','Result','core','std','assert','matches'} for n in interfaces(state['files'])):return False
 data=code.encode();root=parser().parse(data).root_node
 if root.has_error or re.search(r'\bno_implicit_prelude\b',code):return False
 todo=[root]
 while todo:
  node=todo.pop();todo.extend(node.children);text=data[node.start_byte:node.end_byte].decode()
  if node.type in {'macro_definition','extern_crate_declaration'}:return False
  if node.type in {'identifier','type_identifier'} and text in {'Ok','Err','Result','core','std','assert','matches'}:
   if node.parent.type not in {'token_tree','scoped_identifier','scoped_type_identifier','use_wildcard','use_as_clause'} and not (node.parent.type=='macro_invocation' and node.parent.child_by_field_name('macro')==node and text in {'assert','matches'}):return False
  if node.type=='use_declaration':
   # The actual complete candidate API was checked above; other wildcard imports
   # could silently bind standard constructors or assertion macros.
   if '*' in text and not re.fullmatch(r'use\s+i2r_candidate\s*::\s*\*\s*;',text):return False
   if re.search(r'\b(?:Ok|Err|Result|core|assert|matches)\b',text):return False
  if node.type=='attribute_item' and not re.match(r'#\s*\[\s*(?:test|should_panic|cfg|allow)\b',text):
   derives=re.fullmatch(r'#\[derive\(([^)]+)\)\]',text)
   names={n.strip() for n in derives.group(1).split(',')} if derives else set()
   if not names or not names<={'Clone','Copy','Debug','Default','PartialEq','Eq','PartialOrd','Ord','Hash'}:return False
   if any(n.rsplit('::',1)[-1] in names for n in interfaces(state['files'])):return False
 # Also inspect macro token trees for hidden local bindings. Conservative rejection
 # is preferable to inferring name resolution from a constructor spelling.
 if re.search(r'\b(?:let|fn|struct|enum|type|const|static|mod|as)\s+(?:mut\s+)?(?:Ok|Err|Result|core|std|assert|matches)\b',code):return False
 if any(re.search(r'\b(?:Ok|Err|Result|core|std|assert|matches)\b',binding) for binding in re.findall(r'\blet\s+([^=;]+)=',code)):return False
 return True

def exact_i128_pattern(value):
 if not isinstance(value,str):return False
 m=re.fullmatch(r'::core::result::Result::Ok\((-?(?:0|[1-9][0-9_]*)i128)\)',value)
 if not m:return False
 number=int(m.group(1)[:-4].replace('_',''))
 return -(1<<127)<=number<(1<<127)

def target_function(frozen,test):
 if test['kind']!='integration':fail('Result-pattern revision supports standalone integration tests only')
 code=frozen['tests'][test['index']]
 rows=[r for rs in items({'src/lib.rs':code}).values() for r in rs if r['kind']=='function_item' and '::'.join(r['module_scope']+[r['name']])==test['relative_name']]
 if len(rows)!=1:fail('Wrong test must bind one exact function')
 text=rows[0]['text'];start=code.encode().find(text.encode())
 if start<0 or code.encode().find(text.encode(),start+1)>=0:fail('Ambiguous exact test function bytes')
 return code,text,start

def source_tokens(expression):
 data=('fn __f(){let __v = '+expression+';}').encode();root=parser().parse(data).root_node
 if root.has_error:return None
 todo=[root];tokens=[]
 while todo:
  n=todo.pop()
  if not n.children:tokens.append(data[n.start_byte:n.end_byte])
  else:todo.extend(reversed(n.children))
 return tokens

def eligibility(frozen,verdict,state,material,failure):
 checks=full.validate(verdict,frozen,state,material)
 if verdict['action'] not in {'needs_revision','test_wrong'} or any(r['verdict']=='uncertain' for field in checks.values() for r in field.values()):fail('Requires a complete definite source-proven wrong-test judgment')
 inv={r['id']:r for r in full.inventory(frozen)};allowed={}
 if failure.get('status')!='support_contract_failed' or failure.get('compilation',{}).get('status')!='passed':fail('Pattern correction requires the original compiled semantic failure')
 # Rust emits the static assertion expression here. Match its exact tokens to
 # frozen source; no observed left/right value or candidate output is forwarded.
 quoted=re.findall(r'assertion failed: (matches!\([\s\S]*?\))(?=\n(?:note:|\n))',failure.get('diagnostic',''))
 quoted_tokens=[source_tokens(q) for q in quoted]
 if not quoted_tokens or any(q is None for q in quoted_tokens):fail('No exact static failed matches assertion can be bound to frozen test source')
 for name,row in checks['tests'].items():
  if row['verdict']!='wrong':continue
  test=inv[name];code,text,start=target_function(frozen,test)
  if not standard_constructor_scope(code,state):fail('Standard Result/assert/matches binding cannot be established without shadowing',name)
  spans=[s for s in pattern_spans(text) if source_tokens('matches!('+s['actual']+','+s['old_pattern']+')') in quoted_tokens]
  if name not in material['failure_scope']['failed_test_ids'] or len(spans)!=1:fail('Wrong pattern is not uniquely bound to an actual failed static assertion',name)
  if not spans:fail('Wrong test has no supported exact Err pattern',name)
  source_evidence=[e for e in verdict['source_evidence'] if e['id'] in row['basis'] and e['kind']=='source']
  if not source_evidence:fail('API signatures alone cannot justify oracle correction')
  allowed[name]={'test':test,'spans':[{**s,'start':s['start']+start,'end':s['end']+start} for s in spans],'basis':row['basis']}
 if not allowed:fail('No supported wrong-test responsibility')
 return checks,allowed

def apply(frozen,verdict,proposal,state,material,failure):
 checks,allowed=eligibility(frozen,verdict,state,material,failure)
 if set(proposal)-{'action','derivation','pattern_edits','obligation_edits'} or proposal.get('action')!='propose_result_pattern_revision' or not isinstance(proposal.get('derivation'),str) or not proposal['derivation'].strip():fail('Only the exact bounded patch schema is allowed')
 edits=proposal.get('pattern_edits');prose=proposal.get('obligation_edits',[])
 if not isinstance(edits,list) or not edits or not isinstance(prose,list):fail('Missing precise pattern edits')
 updated=deepcopy(frozen);replacements={};edited_tests=set()
 for edit in edits:
  if not isinstance(edit,dict) or set(edit)!={'test_id','actual','old_pattern','new_pattern','basis'}:fail('Pattern edit must name exact test, actual, old/new pattern and existing source basis')
  name=edit['test_id'];entry=allowed.get(name)
  if not entry:fail('Cannot edit a correct/unrelated test',name)
  if not isinstance(edit['basis'],list) or not edit['basis'] or not set(edit['basis'])<=set(entry['basis']) or not any(e['id'] in edit['basis'] and e['kind']=='source' for e in verdict['source_evidence']):fail('Patch lacks the original wrong-test source basis')
  matches=[s for s in entry['spans'] if s['actual']==edit['actual'] and s['old_pattern']==edit['old_pattern']]
  if len(matches)!=1 or not exact_i128_pattern(edit['new_pattern']):fail('Only a unique existing Err pattern to exact standard Ok(i128 literal) is supported')
  span=matches[0];index=entry['test']['index'];key=(span['start'],span['end'])
  if any(a==key for a,b in replacements.get(index,[])):fail('Duplicate edit')
  replacements.setdefault(index,[]).append((key,edit['new_pattern']));edited_tests.add(name)
 if edited_tests!=set(allowed):fail('Every source-proven wrong test must receive its precise correction')
 for index,changes in replacements.items():
  code=frozen['tests'][index].encode()
  for (a,b),new in sorted(changes,reverse=True):code=code[:a]+new.encode()+code[b:]
  updated['tests'][index]=code.decode()
 # Only wrong linked obligation prose can change; IDs/category/disposition/test
 # names and all other obligations stay identical. Preserve all sibling clauses.
 seen=set()
 for edit in prose:
  if not isinstance(edit,dict) or set(edit)!={'id','field','old','new'}:fail('No obligation structure or responsibility changes are permitted')
  oid=edit['id'];row=checks['obligations'].get(oid);field=edit['field'];old=edit['old'];new=edit['new']
  if not row or row['verdict']!='wrong' or not set(row['tests'])<=edited_tests or field not in {'case','expected_basis'} or (oid,field) in seen:fail('Only once-per-field stale prose on a wrong linked obligation may change')
  if not isinstance(old,str) or not isinstance(new,str) or not old.strip() or not new.strip() or old==new or any(x in old+new for x in [';','\n']):fail('Replace one nonempty oracle clause, never a case list')
  if field=='expected_basis' and (len(re.split(r'\.\s+',old.strip().rstrip('.')))>1 or len(re.split(r'\.\s+',new.strip().rstrip('.')))>1):fail('Only one oracle sentence may change; preserve other responsibility prose')
  index=int(oid.split(':')[1]);value=updated['obligations'][index].get(field)
  if not isinstance(value,str) or value.count(old)!=1:fail('Oracle prose replacement must have one exact location')
  updated['obligations'][index][field]=value.replace(old,new,1);seen.add((oid,field))
 # Mechanically prove immutable structure, tests/helpers/calls/inputs and coverage;
 # pattern bytes and narrowly recorded prose replacements are the only writes.
 if full.inventory(updated)!=full.inventory(frozen):fail('Inventory changed during protected revision')
 updated.update(parent_identity=frozen['identity'],oracle_identity=frozen.get('oracle_identity',frozen['identity']),status='source_proven_pattern_revision_pending_independent_check',source_check={'policy':POLICY,'original_judgment':deepcopy(verdict),'model_patch':deepcopy(proposal),'requires_new_scope_acceptance':True})
 updated['identity']=fingerprint({'parent':frozen['identity'],'tests':updated['tests'],'unit_tests':updated.get('unit_tests',[]),'obligations':updated['obligations'],'source_check':updated['source_check']})
 return updated

def verify_repair_receipt(receipt):
 if not isinstance(receipt,dict) or any(not Path(receipt.get(k,'')).is_file() or digest(receipt[k])!=receipt.get(k+'_sha256') for k in ['request','response','call_state']):fail('Patch lacks intact provider archives')
 request=read(receipt['request']);response=read(receipt['response']);call=read(receipt['call_state'])
 if request.get('model')!='deepseek-flash' or call.get('phase')!='source_test_repair' or not isinstance(response,dict) or not response.get('choices') or response['choices'][0].get('finish_reason')!='stop':fail('Patch is not a completed Flash source_test_repair response')

def repair_receipt(provider):
 directory=Path(provider.directory)/f'{provider.calls:03d}'
 record={k:str(directory/name) for k,name in [('request','request.json'),('response','response.json'),('call_state','call-state.json')]}
 for key in ['request','response','call_state']:record[key+'_sha256']=digest(record[key])
 verify_repair_receipt(record);return record


def propose(frozen,verdict,state,material,cfg,provider,directory,failure):
 checks,allowed=eligibility(frozen,verdict,state,material,failure)
 wrong_tests=[r for r in verdict['tests'] if r['id'] in allowed];wrong_obs=[r for r in verdict['obligations'] if r['verdict']=='wrong'];basis={b for r in wrong_tests+wrong_obs for b in r['basis']}
 evidence=[r for r in verdict['source_evidence'] if r['id'] in basis];source_ids={r['source'] for r in evidence if r['kind']=='source'}
 request={'task':'Propose only a source-proven Err-pattern→exact ::core::result::Result::Ok(<signed decimal i128 literal>) patch. Keep assert!(matches!) and its actual expression byte-identical, retain every other assertion including real overflow cases. Optional stale obligation case/expected_basis correction: one exact clause/sentence per wrong field, no semicolons/newlines or responsibility deletion. No new cases, no whole-test replacement. Return unresolved if this rule cannot safely express the correction.',
 'schema':{'action':'propose_result_pattern_revision','derivation':'source-based explanation','pattern_edits':[{'test_id':'exact wrong test ID','actual':'exact existing actual expression','old_pattern':'exact Err(...)','new_pattern':'::core::result::Result::Ok(<source-derived integer>i128)','basis':['existing source evidence ID']}],'obligation_edits':[{'id':'o:index','field':'case | expected_basis','old':'one exact wrong clause/sentence','new':'corrected same-responsibility clause/sentence'}]},
 'completed_independent_judgment':{'action':verdict['action'],'tests':wrong_tests,'obligations':wrong_obs,'source_evidence':evidence},'source':[p for p in material['source'] if p['source'] in source_ids],
 'numeric_policy':material['numeric_policy'],'interfaces':material['interfaces'],'tests':material['tests'],'unit_tests':material['unit_tests'],
 'obligations':[r for r in material['obligations'] if r['id'] in {o['id'] for o in wrong_obs}],
 'permitted_locations':{n:[{k:v for k,v in s.items() if k not in {'start','end'}} for s in r['spans']] for n,r in allowed.items()}}
 key=fingerprint({'policy':POLICY,'system':SYSTEM,'request':request,'model':cfg['model'],'generation':cfg['generation'],'suite':frozen['identity']});path=Path(directory)/key;path.mkdir(parents=True,exist_ok=True);record_path=path/'record.json'
 if record_path.exists() and read(record_path).get('status')=='completed':
  record=read(record_path);verify_repair_receipt(record['provider_receipt'])
  if read(path/'input.json')!=request or digest(path/'proposal.json')!=record['proposal_sha256']:fail('Protected repair proposal scope or bytes changed')
  proposal=read(path/'proposal.json')
 else:
  record=read(record_path) if record_path.exists() else {'policy':POLICY,'scope':key,'not_semantic_judgment':True,'attempts':[]}
  if record.get('status')=='unresolved_response':fail('Prior pattern proposal was incomplete/invalid; no blind repeat',record)
  record['status']='reserved';save(record_path,record);save(path/'input.json',request)
  before=provider.calls;started=time.monotonic();usage=deepcopy(provider.usage)
  try:
   conversation=Conversation(path/'isolated-conversation.json',cfg);conversation.enter('source-test-pattern-repair')
   proposal=conversation.call(provider,SYSTEM,request,path/'request',phase='source_test_repair')
  except Failure as error:
   record.update(status='interrupted' if error.code in {'provider_error','provider_protocol_error','budget_exhausted'} else 'unresolved_response',error={'code':error.code,'message':str(error)})
   raise
  finally:
   record['resources']={'calls':provider.calls-before,'seconds':time.monotonic()-started,'usage_before':usage,'usage_after':deepcopy(provider.usage)};record.setdefault('attempts',[]).append(deepcopy(record['resources']));save(record_path,record)
  save(path/'proposal.json',proposal);record.update(status='completed',proposal_sha256=digest(path/'proposal.json'),provider_receipt=repair_receipt(provider));save(record_path,record)
 updated=apply(frozen,verdict,proposal,state,material,failure);updated['source_check']['patch_provider_receipt']=record['provider_receipt'];updated['source_check']['patch_path']=str(path)
 save(path/'protected-revision.json',updated);return updated
