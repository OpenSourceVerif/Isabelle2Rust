"""Review-only conservative Rust function/dependency projection.
Never modifies the executable frozen suite. Ambiguity keeps the entire artifact.
"""
from copy import deepcopy
import re,hashlib
from .task_context import fingerprint
from .source_test_context import bodyless_interfaces,canonical_mapping
from .segmented_contract import PRIMITIVES
POLICY='exact-failed-function-review-projection-imports-v2'
BUILTINS=set(PRIMITIVES)|{'Ok','Err','Some','None','Vec','String','Box','Option','Result','Self','Clone','Copy','Debug','Default','PartialEq','Eq','PartialOrd','Ord','Hash','Sized','Send','Sync','Fn','FnMut','FnOnce','Iterator','IntoIterator','From','Into','TryFrom','TryInto','Drop','__projection','__args'}
MACROS={'assert','assert_eq','assert_ne','matches','vec','panic'}
class Ambiguous(Exception):pass

def _parser():
 from tree_sitter import Language,Parser
 import tree_sitter_rust
 return Parser(Language(tree_sitter_rust.language()))
def _hash(data):return hashlib.sha256(data).hexdigest()
def _names(node,data):
 todo=[node];out=set()
 while todo:
  n=todo.pop();todo.extend(n.named_children)
  if n.type in {'identifier','type_identifier'}:out.add(data[n.start_byte:n.end_byte].decode())
 return out

def _candidate_import_paths(text,api):
 # Deliberately accept only exact, unaliased single paths or one flat group.
 # No module imports, reexports, wildcard, self/super, aliases or nested groups.
 ident=r'[A-Za-z_][A-Za-z_0-9]*'
 match=re.fullmatch(r'use\s+(i2r_candidate(?:::'+ident+r')*)\s*::\s*\{\s*('+ident+r'(?:\s*,\s*'+ident+r')*\s*,?)\s*\}\s*;',text)
 if match:
  paths=[match.group(1)+'::'+name.strip() for name in match.group(2).rstrip().rstrip(',').split(',')]
 else:
  match=re.fullmatch(r'use\s+(i2r_candidate(?:::'+ident+r')+)\s*;',text)
  if not match:raise Ambiguous('Unknown/aliased import requires full artifact')
  paths=[match.group(1)]
 canonical=['crate::'+path.removeprefix('i2r_candidate::') for path in paths]
 if any(path not in api for path in canonical):raise Ambiguous('Candidate import lacks an exact public interface')
 return canonical

def _project_code(code,target_names,api):
 data=code.encode();parser=_parser();root=parser.parse(data).root_node
 if root.has_error:raise Ambiguous('Rust parse error')
 rows=[];attrs=[];byname={};imports=set();candidate_imports={};api_leaf={}
 for name in api:api_leaf.setdefault(name.rsplit('::',1)[-1],[]).append(name)
 for node in root.named_children:
  if node.type in {'line_comment','block_comment'}:continue
  if node.type=='attribute_item':attrs.append(node);continue
  if node.type not in {'function_item','struct_item','enum_item','type_item','const_item','static_item','trait_item','impl_item','use_declaration','mod_item'}:raise Ambiguous('Unsupported top-level Rust item '+node.type)
  attrtext=' '.join(data[a.start_byte:a.end_byte].decode() for a in attrs)
  if attrs and any(not re.match(r'#\s*\[\s*(?:test|should_panic|allow|derive)\b',data[a.start_byte:a.end_byte].decode()) for a in attrs):raise Ambiguous('Conditional/procedural attribute requires full artifact')
  for attr in attrs:
   text=data[attr.start_byte:attr.end_byte].decode()
   if re.match(r'#\s*\[\s*derive\b',text):
    match=re.fullmatch(r'#\s*\[\s*derive\(([^)]+)\)\s*\]',text)
    names={n.strip() for n in match.group(1).split(',')} if match else set()
    if not names or not names<={'Clone','Copy','Debug','Default','PartialEq','Eq','PartialOrd','Ord','Hash'} or any(n in api_leaf for n in names):raise Ambiguous('Unknown/shadowed derive macro')
  name_node=node.child_by_field_name('name');name=data[name_node.start_byte:name_node.end_byte].decode() if name_node else None
  row={'node':node,'start':attrs[0].start_byte if attrs else node.start_byte,'end':node.end_byte,'kind':node.type,'name':name,'test':bool(re.search(r'#\s*\[\s*test\s*\]',attrtext))};attrs=[];rows.append(row)
  if name:
   if name in byname:raise Ambiguous('Duplicate top-level identifier '+name)
   byname[name]=row
  if node.type=='use_declaration':
   text=data[node.start_byte:node.end_byte].decode()
   if '*' in text and not re.fullmatch(r'use\s+i2r_candidate\s*::\s*\*\s*;',text):raise Ambiguous('Unknown wildcard import')
   if '*' not in text:
    # Keep imports verbatim; resolve only simple std/core or exact candidate items.
    m=re.fullmatch(r'use\s+(?:(?:std|core)::)([A-Za-z_][\w:]*)\s*;',text)
    if m:
     leaf=m.group(1).rsplit('::',1)[-1]
     if leaf in imports or leaf in candidate_imports or leaf in api_leaf:raise Ambiguous('Shadowed import requires full artifact')
     imports.add(leaf)
    else:
     for path in _candidate_import_paths(text,api):
      leaf=path.rsplit('::',1)[-1]
      if leaf in imports or leaf in candidate_imports or api_leaf.get(leaf)!=[path]:raise Ambiguous('Ambiguous candidate import requires full artifact')
      candidate_imports[leaf]=path
 if set(candidate_imports)&set(byname):raise Ambiguous('Local item shadows candidate import')
 if attrs:raise Ambiguous('Dangling attributes')
 if any(n not in byname or not byname[n]['test'] for n in target_names):raise Ambiguous('Target is not an exact top-level test')
 selected={rows.index(byname[n]) for n in target_names}|{i for i,r in enumerate(rows) if r['kind'] in {'use_declaration','impl_item'}};done=set();api_refs=set()
 def resolve(name,locals,call=False):
  if name in locals:
   if call or name in byname or name in api_leaf:raise Ambiguous('Dynamic or shadowed local reference '+name)
   return
  if name in byname:
   row=byname[name]
   if row['test'] and name not in target_names:raise Ambiguous('Cross-test function reference '+name)
   selected.add(rows.index(row));return
  if name in api_leaf:
   if len(api_leaf[name])!=1:raise Ambiguous('Ambiguous candidate item '+name)
   api_refs.add(api_leaf[name][0]);return
  if name in BUILTINS or name in imports:return
  raise Ambiguous('Unresolved Rust identifier '+name)
 def scan(node,raw,locals,depth=0):
  if depth>20:raise Ambiguous('Macro nesting requires full artifact')
  spelling=raw[node.start_byte:node.end_byte].decode()
  if node.type in {'let_declaration','parameter'}:
   pattern=node.child_by_field_name('pattern')
   if pattern and _names(pattern,raw)&set(candidate_imports):raise Ambiguous('Local binding shadows candidate import')
  if node.type in {'line_comment','block_comment','attribute_item','field_identifier','label','lifetime','string_literal','raw_string_literal','char_literal','integer_literal','float_literal','boolean_literal'}:return
  if node.type=='macro_invocation':
   macro=node.child_by_field_name('macro');name=raw[macro.start_byte:macro.end_byte].decode()
   if name not in MACROS:raise Ambiguous('Unknown macro '+name)
   body=next((x for x in node.children if x.type=='token_tree'),None)
   if body is None:raise Ambiguous('Missing macro tokens')
   inner=raw[body.start_byte+1:body.end_byte-1].decode()
   if name=='matches':
    commas=[x for x in body.children if x.type==',']
    if len(commas) not in {1,2}:raise Ambiguous('Ambiguous matches token structure')
    a=raw[body.start_byte+1:commas[0].start_byte].decode();b=raw[commas[0].end_byte:(commas[1].start_byte if len(commas)>1 else body.end_byte-1)].decode();expr='match '+a+' { '+b+' => true, _ => false }'
   elif name=='vec':expr='['+inner+']'
   else:expr='__args('+inner+')'
   chunk=('fn __projection(){'+expr+';}').encode();parsed=parser.parse(chunk).root_node
   if parsed.has_error:raise Ambiguous('Unresolved macro expression semantics')
   scan(parsed,chunk,locals,depth+1);return
  if node.type=='call_expression':
   f=node.child_by_field_name('function')
   if f.type not in {'identifier','scoped_identifier'}:raise Ambiguous('Method/generic/dynamic call needs full artifact')
   if f.type=='identifier':resolve(raw[f.start_byte:f.end_byte].decode(),locals,True)
   else:
    path=raw[f.start_byte:f.end_byte].decode().removeprefix('::');base=path.split('::')[0]
    if 'crate::'+path.removeprefix('crate::') not in api and base not in {'std','core','Result','Option'}|set(PRIMITIVES):raise Ambiguous('Unresolved associated/trait method requires full artifact')
  if node.type in {'scoped_identifier','scoped_type_identifier'}:
   path=spelling.removeprefix('::');parts=path.split('::');base=parts[0]
   if base in {'std','core'} or base in PRIMITIVES or base in {'Self','Result','Option'}:return
   exact='crate::'+path.removeprefix('crate::')
   if exact in api:api_refs.add(exact);return
   resolve(base,locals);return
  if node.type in {'identifier','type_identifier'}:
   parent=node.parent
   if parent and parent.child_by_field_name('name')==node:return
   resolve(spelling,locals);return
  for child in node.named_children:scan(child,raw,locals,depth)
 while selected-done:
  i=min(selected-done);done.add(i);row=rows[i];node=row['node']
  if row['kind']=='use_declaration':continue
  if row['kind']=='mod_item':raise Ambiguous('Module helper requires whole artifact')
  locals=set();todo=[node]
  while todo:
   n=todo.pop();todo.extend(n.named_children)
   if n.type in {'let_declaration','parameter'}:
    pattern=n.child_by_field_name('pattern')
    if pattern:locals|=_names(pattern,data)
   elif n.type in {'closure_expression','function_type'}:raise Ambiguous('Closure/function value requires whole artifact')
   elif n.type=='type_parameters':locals|=_names(n,data)
  scan(node,data,locals)
 selected_rows=[r for i,r in enumerate(rows) if i in selected]
 text='\n\n'.join(data[r['start']:r['end']].decode() for r in selected_rows)+'\n'
 spans=[{k:r[k] for k in ['start','end','name','test']}|{'item_kind':r['kind'],'sha256':_hash(data[r['start']:r['end']])} for r in selected_rows]
 return text,spans,sorted(api_refs)

def build(frozen,failed,legacy_scope,legacy_inventory,legacy_obligations,state):
 api=bodyless_interfaces(state);all_inv={r['id']:r for r in legacy_inventory};wanted=set(failed);sources=set();changed=True;force_fallback=None
 # A multi-test obligation representation is not silently flattened to test_name.
 # Keep the entire actual suite when its association cannot be resolved by this
 # deliberately narrow top-level function projection.
 if any(any(k in o for k in ['tests','test_names']) for o in frozen['obligations']):
  from .source_suite_review import inventory
  legacy_inventory=inventory(frozen);legacy_obligations=[{'id':f'o:{i}','claim':o} for i,o in enumerate(frozen['obligations'])]
  legacy_scope={**legacy_scope,'artifacts':[{'kind':'integration','index':i} for i in range(len(frozen['tests']))]+[{'kind':'unit','index':i} for i in range(len(frozen.get('unit_tests',[])))],'test_ids':[r['id'] for r in legacy_inventory],'obligation_ids':[r['id'] for r in legacy_obligations]}
  all_inv={r['id']:r for r in legacy_inventory};force_fallback='Multi-test obligation association retains complete execution suite'

 if not wanted or not wanted<=all_inv.keys():
  from .common import Failure
  raise Failure('source_check_unresolved','Missing failed test identity')
 # Any actual shared responsibility is retained with its associated tests.
 while changed:
  before=set(wanted)
  sources|={r['claim']['source'] for r in legacy_obligations if r['claim'].get('test_name') in wanted}
  for row in legacy_obligations:
   claim=row['claim'];names=set(claim.get('tests',[])) if isinstance(claim.get('tests',[]),list) else set()
   if names&wanted and names<=all_inv.keys():wanted|=names
  if not wanted<=all_inv.keys():force_fallback='Cross-scope obligation association'
  changed=before!=wanted
 selected_inv=[r for r in legacy_inventory if r['id'] in wanted]
 selected_obs=[r for r in legacy_obligations if r['claim'].get('test_name') in wanted or r['claim'].get('source') in sources and r['claim'].get('disposition') in {'not_applicable','inaccessible'}]
 identity=fingerprint({k:frozen.get(k) for k in ['tests','unit_tests','obligations','test_framework','source_contract_templates','author_group_plan']})
 base={'policy':POLICY,'original_suite_material_identity':identity,'original_artifact_hashes':[{'kind':a['kind'],'index':a['index'],'sha256':_hash((frozen['tests'][a['index']] if a['kind']=='integration' else frozen['unit_tests'][a['index']]['source']).encode())} for a in legacy_scope['artifacts']],'full_bodyless_api_identity':fingerprint(api),'canonical_mapping_identity':fingerprint(canonical_mapping(state))}
 try:
  if force_fallback:raise Ambiguous(force_fallback)
  if not selected_obs:raise Ambiguous('No complete associated obligation')
  if any(r['kind']!='integration' or '::' in r['relative_name'] for r in selected_inv):raise Ambiguous('Private/nested unit test requires full artifact')
  tests=[];spans=[];refs=set()
  for a in legacy_scope['artifacts']:
   names={r['relative_name'] for r in selected_inv if (r['kind'],r['index'])==(a['kind'],a['index'])}
   if not names:raise Ambiguous('Cross-artifact/helper-only input retains full original artifacts')
   text,parts,used=_project_code(frozen['tests'][a['index']],names,api);tests.append({'index':a['index'],'source':text});refs.update(used)
   spans.extend({**a,**part} for part in parts)
  projection={**base,'mode':'exact_function_dependency_closure','retained_test_ids':sorted(wanted),'retained_obligation_ids':[r['id'] for r in selected_obs],'source_spans':spans,'referenced_candidate_items':sorted(refs),'omitted_execution_test_ids':sorted(set(all_inv)-wanted),'execution_suite_unchanged':True}
  return {'projection':projection,'inventory':selected_inv,'obligations':selected_obs,'tests':tests,'unit_tests':[]}
 except Ambiguous as error:
  projection={**base,'mode':'full_artifact_fallback','reason':str(error),'retained_test_ids':legacy_scope['test_ids'],'retained_obligation_ids':legacy_scope['obligation_ids'],'execution_suite_unchanged':True}
  return {'projection':projection,'inventory':legacy_inventory,'obligations':legacy_obligations,'tests':[{'index':a['index'],'source':frozen['tests'][a['index']]} for a in legacy_scope['artifacts'] if a['kind']=='integration'],'unit_tests':[{'index':a['index'],**frozen['unit_tests'][a['index']]} for a in legacy_scope['artifacts'] if a['kind']=='unit']}
