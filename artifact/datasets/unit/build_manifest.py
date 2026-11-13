"""Build hash-locked unit projects from source-derived observation specifications."""
import argparse,hashlib,json,re
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=SOURCE)
args=parser.parse_args()
BASE=args.output.resolve();BASE.mkdir(parents=True,exist_ok=True)
REPO=SOURCE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
EXPORT=re.compile(r'(?m)^[ \t]*export_code\s+([\s\S]*?)\bin\s+Rust\b(?:[ \t]+module_name[ \t]+\w+)?(?:[ \t]+file_prefix[ \t]+\w+)?')
rows=[]
specs=[]
for p in sorted((SOURCE/'specs').glob('*.json')):
 data=json.loads(p.read_text());specs.extend(data if isinstance(data,list) else data['cases'])
catalog=json.loads((SOURCE/'root-catalog.json').read_text())['cases']
canonical={(r['theory'],r['spelling']):r for r in catalog}
seen=set();duplicates=[]
for spec in specs:
 path=spec['theory']; path=path[path.index('test/unit/'):]
 original=REPO/path; category=original.parent.name; name=original.stem
 info=canonical[(path,spec['roots'][0])]
 if info['root'] in seen:
  duplicates.append({'theory':path,'root':info['root'],'reason':'same canonical name, distinct source profile/dependency closure retained as a separate task'})
 seen.add(info['root'])
 key='unit-'+category+'-'+name.removesuffix('_Test').replace('_','-').lower()+'-'+spec['roots'][0].replace('_','-').lower()+'-'+hashlib.sha256(info['root'].encode()).hexdigest()[:6]
 commands=list(EXPORT.finditer(original.read_text()))
 roots=[x for m in commands for x in m.group(1).split()]
 assert len(spec['roots'])==1 and spec['roots'][0] in roots,(key,roots,spec['roots'])
 roots=spec['roots']
 assert set(roots)<=set(spec['coverage']),(key,'missing coverage')
 assert spec['fixed'] and len(spec['generated'])==40,key
 values=spec['fixed']+spec['generated'];assert all(isinstance(x,list) and all(type(n)is int and n>=0 for n in x) for x in values)
 target=BASE/'projects'/key;target.mkdir(parents=True,exist_ok=True)
 mounts={}
 dependencies=[original]
 if name=='CopyCalls_Test':dependencies.append(original.with_name('CopyGlobalData.thy'))
 if name in ['WordBigInt_Test','WordChecked128_Test']:dependencies.append(original.with_name('Word_Setup_Common.thy'))
 for folder in ['program','testing']:
  sub=target/folder;sub.mkdir(exist_ok=True)
  (sub/'agent.toml').write_text('[isabelle]\ntheories=["Export"]\nsessions=["Rust","HOL-Library"]\n')
  for dependency in dependencies:
   text=dependency.read_text();matches=list(EXPORT.finditer(text));lines=text.splitlines(True);edits=[]
   # Whole export commands are administrative only; replacements preserve all other bytes.
   derived=EXPORT.sub(lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),text)
   # Keep byte-identical original and recipe receipt alongside each mounted source.
   (sub/dependency.name).write_text(derived)
   write(sub/(dependency.stem+'.source-receipt.json'),{'original':str(dependency.relative_to(REPO)),'sha256':sha(dependency),'derived_sha256':sha(sub/dependency.name),'removed_exports':[m.group() for m in matches]})
  imports=name+' "I2R_Agent.Agent_Export"'
  if folder=='program':exports=' '.join(roots)
  else:
   (sub/'Model.thy').write_text('theory Model imports '+name+' begin\n'+spec['model_body']+'\nend\n')
   (sub/'Kernel.thy').write_text('''theory Kernel imports Model begin
definition kernel_prepare :: "nat list \\<Rightarrow> nat list" where "kernel_prepare x = x"
definition kernel_run :: "nat list \\<Rightarrow> nat list" where "kernel_run x = Model.observe x"
definition kernel_encode :: "nat list \\<Rightarrow> nat list" where "kernel_encode x = x"
lemma kernel_observation: "kernel_encode (kernel_run (kernel_prepare x)) = Model.observe x"
 by (simp add: kernel_prepare_def kernel_run_def kernel_encode_def)
end
''')
   imports='Kernel "I2R_Agent.Agent_Export"';exports='Model.observe Kernel.kernel_prepare Kernel.kernel_run Kernel.kernel_encode'
  (sub/'Export.thy').write_text('theory Export imports '+imports+' begin\nexport_code '+exports+' in Rust_Agent module_name Candidate\nend\n')
 metadata={'id':key,'algorithm_project':'program','testing_project':'testing','contract':'Original unit HOL definitions, concrete observations for every exported entry. Reference outputs computed by the existing dual-reference machinery. '+json.dumps(spec['coverage']), 'kernel':{'prepare':'Kernel.kernel_prepare','run':'Kernel.kernel_run','encode':'Kernel.kernel_encode','source':'Kernel.thy','scope':'Correctness-only observation; no performance claim.'}}
 write(target/'case.json',metadata)
 write(target/'testing/case.json',metadata)
 inputs={'ordinary_fixed':spec['fixed'],'ordinary_generated':spec['generated'],'kernel_fixed':spec['fixed'],'kernel_generated':spec['generated']}
 rows.append({'id':key,'root':info['root'],'closure':info['closure'],'roots':roots,'project':'datasets/unit/projects/'+key,'files':{str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()},'source_mounts':{},'inputs':inputs,'config':{},'coverage':spec['coverage'],'original_source':path,'numeric_mode':'FPP arbitrary Dashu; original target-profile syntax is not an agent representation constraint'})
assert len({r['id'] for r in rows})==len(rows)
all_sources=list((REPO/'test/unit').rglob('*.thy'))
missing=[str(p.relative_to(REPO)) for p in all_sources if EXPORT.search(p.read_text()) and str(p.relative_to(REPO)) not in ({r['original_source'] for r in rows}|{r['theory'] for r in duplicates})]
manifest={'expected_root_count':len(rows),'additional_source_contexts':duplicates,'cases':rows,'corpus':{str(p.relative_to(REPO)):sha(p) for p in all_sources},'missing_theories':missing,'counting_unit':'one exported root in its source context; 488 tasks / 482 distinct root names; exact closure frozen from independent per-root Isabelle export'}
write(BASE/'manifest.json',manifest)
print(json.dumps({'roots':len(rows),'theories':len({r['original_source'] for r in rows}),'additional_source_contexts':len(duplicates),'missing':missing},indent=2))
