"""Immutable source-test expectation slots. IDs select locations, never permissions."""
import hashlib
from .common import Failure
from .task_context import fingerprint
POLICY='scope-artifact-test-bound-expected-slot-v1'

def fail(message):raise Failure('source_check_unresolved',message)

def locations(frozen,state,allowed=None):
 from .source_suite_review import inventory
 from .source_failure_check import expected_spans,protected_expected_pair
 from .segmented_contract import items
 out=[]
 for test in inventory(frozen):
  if allowed is not None and test['id'] not in allowed:continue
  kind,index=test['kind'],test['index'];code=frozen['tests'][index] if kind=='integration' else frozen['unit_tests'][index]['source'];data=code.encode()
  functions=[r for rows in items({'src/lib.rs':code}).values() for r in rows if r['kind']=='function_item' and '::'.join(r['module_scope']+[r['name']])==test['relative_name']]
  if len(functions)!=1:continue  # No editable slot; the full checker still sees the test.
  fn=functions[0]['text'];raw=fn.encode();base=data.find(raw)
  if base<0 or data.find(raw,base+1)>=0:continue  # Never guess among duplicate bodies.
  spans=sorted(set(expected_spans(fn,helper_context=code,state=state)))
  for ordinal,(a,b,old) in enumerate(spans):
   # A slot is only a supported protected expected value; candidate calls and
   # variables cannot acquire edit permission merely by receiving an ID.
   if not protected_expected_pair(old,old,code,kind,state):continue
   start,end=base+a,base+b
   out.append({'kind':kind,'index':index,'test_id':test['id'],'artifact_sha256':hashlib.sha256(data).hexdigest(),'test_sha256':hashlib.sha256(raw).hexdigest(),'expected_ordinal':ordinal,'start_byte':start,'end_byte':end,'old':old,'context':data[max(base,start-110):min(base+len(raw),end+40)].decode(errors='replace')})
 return out

def catalog(frozen,state,material):
 # Bind the exact original suite, selected scope, source pages and public API.
 scope=fingerprint({k:v for k,v in material.items() if k!='expectation_targets'})
 suite=fingerprint({k:frozen.get(k) for k in ['identity','tests','unit_tests','obligations']})
 rows=locations(frozen,state,{r['id'] for r in material['inventory']})
 for row in rows:
  row['target_id']=fingerprint({'policy':POLICY,'scope':scope,'suite':suite,**{k:v for k,v in row.items() if k!='context'}})
 bindings={row['test_id']:{k:row[k] for k in ['kind','index','artifact_sha256','test_sha256']} for row in rows}
 compact=[{k:v for k,v in row.items() if k not in {'artifact_sha256','test_sha256'}} for row in rows]
 return {'policy':POLICY,'scope_sha256':scope,'suite_sha256':suite,'tests':bindings,'slots':compact}

def attach(frozen,state,material):
 return {**material,'expectation_targets':catalog(frozen,state,material)}

def resolve(frozen,state,material,edit):
 kind,index=edit.get('kind'),edit.get('index');old=edit.get('old');target=edit.get('target_id')
 if target is not None:
  if set(edit)-{'target_id','kind','index','test_id','old','new'}:fail('Expected target edits cannot supply offsets or extra mutation fields')
  if type(index) is not int:fail('Expected target artifact index must be an integer')
  if not material or not isinstance(target,str):fail('Expected target needs its exact supplied checker scope')
  actual=catalog(frozen,state,material)
  if material.get('expectation_targets')!=actual:fail('Expected target catalog is stale or altered')
  matches=[r for r in actual['slots'] if r['target_id']==target]
  if len(matches)!=1:fail('Unknown/stale expected target ID')
  row=matches[0]
  if any(edit.get(k)!=row[k] for k in ['kind','index','test_id','old']):fail('Expected target does not match artifact/test/original expectation')
  return row['start_byte'],row['end_byte'],row['old']
 # Legacy unique literals stay valid. Repeated values never pick the first slot.
 from .source_failure_check import expected_spans
 seq=frozen['tests'] if kind=='integration' else frozen.get('unit_tests',[]) if kind=='unit' else []
 if type(index) is not int or not 0<=index<len(seq):fail('Invalid expectation artifact index')
 code=seq[index] if kind=='integration' else seq[index]['source']
 if edit.get('test_id'):
  candidates=locations(frozen,state,{edit['test_id']})
  matches=[(r['start_byte'],r['end_byte'],r['old']) for r in candidates if r['kind']==kind and r['index']==index and r['old']==old]
 else:matches=[r for r in expected_spans(code,state=state) if r[2]==old]
 if len(matches)!=1:fail('Edit must identify exactly one expected argument; repeated literals require an exact target_id')
 return matches[0]

def plan(frozen,state,material,edits):
 rows=[];occupied={}
 for edit in edits:
  span=resolve(frozen,state,material,edit);key=(edit['kind'],edit['index'])
  if any(not(span[1]<=a or b<=span[0]) for a,b in occupied.setdefault(key,[])):fail('Duplicate or overlapping expectation targets')
  occupied[key].append(span[:2]);rows.append((edit,span))
 # Resolve every slot against the original suite, then edit backwards so an
 # earlier replacement cannot relocate or impersonate a later target.
 return sorted(rows,key=lambda item:(item[0]['kind'],item[0]['index'],item[1][0]),reverse=True)
