"""Run the eight catalogue cases with AFP Go, using the shared kernel protocol.

Invoke with python -m i2r_agent.go_baseline. Existing reference observations and
measurements retain their versions; Go artifacts live beside OCaml and Stage 2
under their exact baseline, with independent build attempts and timestamps.
"""
from pathlib import Path
import hashlib,json,re,shutil,sys
from .common import ROOT,Executor,Failure,config,digest,now,read,save
from .preprocessing import project_info,isabelle_command
from .baselines import fingerprint,cached_outputs,measure_once,valid_record,language_artifacts
from .validation import execute
from .performance import benchmark
from .native_baseline import baseline_for
from . import suites

DRIVER = '''package main
import (
 "bufio"
 "fmt"
 "os"
 "strings"
 "time"
 C "isabelle/exported/Candidate"
 B "isabelle/exported/Bigint"
)
func main() {
 measuring := len(os.Args)>1 && os.Args[1]=="--i2r-benchmark"
 scanner:=bufio.NewScanner(os.Stdin)
 scanner.Buffer(make([]byte,4096),64*1024*1024)
 for scanner.Scan() {
  words:=strings.Fields(scanner.Text())
  var input C.List[C.Nat] = C.Nil[C.Nat]{}
  for i:=len(words)-1;i>=0;i-- { input=C.Cons[C.Nat]{A:C.Nat_of_integer(B.MkInt(words[i])), Aa:input} }
  var output C.List[C.Nat]
  if measuring {
   prepared:=C.Kernel_prepare(input)
   start:=time.Now()
   result:=C.Kernel_run(prepared)
   elapsed:=time.Since(start).Nanoseconds()
   fmt.Fprintf(os.Stderr,"I2R_KERNEL_NS %d\\n",elapsed)
   output=C.Kernel_encode(result)
  } else { output=C.Observe(input) }
  encoded:=[]string{}
  for { node,ok:=output.(C.Cons[C.Nat]); if !ok {break}; n:=C.Integer_of_nat(node.A);encoded=append(encoded,n.String());output=node.Aa }
  fmt.Println(strings.Join(encoded," "))
 }
 if err:=scanner.Err();err!=nil {panic(err)}
}
'''

def run_case(case,cfg,run):
 project,base=baseline_for(case)
 go=Path(cfg['tools']['afp'])/'Go'
 identity={'sources':base['identity']['sources'],'go_sources':{str(p):digest(p) for p in [go/'Go_Setup.thy',go/'code_go.ML']},'driver':fingerprint(DRIVER),'runner':digest(__file__),'base_id':base['id'],'config':cfg,'protocol':cfg['performance'].get('protocol','kernel-v1')}
 work=language_artifacts(base['id'],'go',ROOT)/run.name;work.mkdir(parents=True,exist_ok=True);ex=Executor(work/'logs')
 version=ex.run([cfg['tools']['isabelle'],'go','version']);identity['go_version']=Path(version['stdout']).read_text().strip()
 result={'case':case,'status':'running','started_at':now(),'identity':identity,'baseline_id':base['id'],'measurement_id':run.name+'/'+case}
 save(work/'result.json',result)
 try:
  build=work/'isabelle';build.mkdir(exist_ok=True)
  for p in project.glob('*.thy'):shutil.copy2(p,build/p.name)
  p=build/'Export.thy'
  p.write_text(p.read_text().replace('"I2R_Agent.Agent_Export"','"Go.Go_Setup" "HOL-Library.Code_Target_Nat"').replace('in Rust_Agent','nat_of_integer integer_of_nat in Go'))
  theories,sessions=project_info(project);sessions=sorted(set(sessions)-{'I2R_Agent'}|{'HOL-Library'})
  session='I2R_Go_'+case.replace('-','_')+'_'+fingerprint(identity)[:10]
  (build/'ROOT').write_text(f'session {session} = Go +\n options [document=false]\n sessions '+ ' '.join('"'+s+'"' for s in sessions)+'\n theories '+ ' '.join(theories)+'\n export_files (in "exported") [2] "*:code/**"\n')
  ex.run(isabelle_command(cfg,'build','-e','-j','1','-o','threads=2','-d',cfg['tools']['afp'],'-d',build,session),timeout=1200)
  module=next((build/'exported').rglob('go.mod')).parent
  (module/'main.go').write_text(DRIVER)
  binary=work/'reference'
  ex.run([cfg['tools']['isabelle'],'go','build','-o',binary,'.'],cwd=module,timeout=300)
  seed=cfg['testing']['seed']+int(hashlib.sha256(case.encode()).hexdigest()[:6],16)
  reg={}
  for p in (ROOT/'data/runs').glob('*/inputs/'+case+'/regressions.json'):
   for x in read(p):
    if suites.domain(case,x['input']):reg[json.dumps(x['input'])]=x['input']
  groups={'fixed':suites.fixed(case),'regression':list(reg.values()),'generated':suites.generate(case,cfg['testing']['random_cases'],seed),'final':suites.generate(case,cfg['testing']['final_cases'],seed+1000003)}
  checks=[]
  for kind,inputs in groups.items():
   save(work/(kind+'-inputs.json'),inputs)
   expected=cached_outputs(case,inputs,base['references'],ex,cfg['testing']['process_timeout'])['ocaml']['outputs']
   for label,args in [('observer',()),('kernel',('--i2r-benchmark',))]:
    actual=execute(binary,inputs,ex,cfg['testing']['process_timeout'],args)
    ok=actual['status']=='passed' and actual['outputs']==expected
    checks.append({'suite':kind,'path':label,'count':len(inputs),'status':'passed' if ok else 'failed','execution':actual['record']})
    save(work/'checks.json',checks)
    if not ok:raise Failure('go_behavior_failed',kind+' '+label,actual)
  workload=suites.scoped_performance_input(case,cfg['performance'].get('input_bits',128))
  expected=cached_outputs(case,[workload],base['references'],ex,15)['ocaml']['outputs'][0]
  reference_measurement=measure_once(base,workload,expected,cfg,ex)
  perf=benchmark({'go':str(binary)},workload,expected,cfg,ex,work)
  if perf['protocol']['version']=='kernel-v1':perf['protocol']['timer']='Go time.Now/time.Since monotonic clock; ordinary timer-call overhead is not subtracted'
  perf.update(measured_at=now(),acquisition='measured_once',origin=str(work/'performance.json'))
  save(work/'performance.json',perf)
  result.update(status='passed',checks=checks,performance=perf,reference_measurement=reference_measurement['record_path'],reference={'binary':str(binary),'binary_sha256':digest(binary),'source':str(module/'Candidate/exported.go'),'sha256':digest(module/'Candidate/exported.go'),'timing_protocol':'kernel-v1'},generated_hashes={str(p.relative_to(module)):digest(p) for p in module.rglob('*') if p.is_file()})
 except Exception as e:
  result.update(status='failed',error=str(e),error_code=getattr(e,'code',type(e).__name__),evidence=getattr(e,'evidence',None))
 result['finished_at']=now();save(work/'result.json',result);return result

def migrate_storage(root=ROOT):
 """Relocate historical evidence without building or measuring anything.

 Only storage paths change; identities, source hashes, timings and timestamps
 remain intact. Callers should archive the original tree before migration.
 """
 root=Path(root);legacy=root/'data/go-baselines';moves=[]
 for path in sorted(legacy.glob('*/*/result.json')):
  result=read(path)
  destination=language_artifacts(result['baseline_id'],'go',root)/path.parent.parent.name
  if not (root/'data/baselines'/result['baseline_id']/'baseline.json').is_file():
   raise Failure('baseline_missing','Cannot relocate '+str(path))
  if destination.exists():raise Failure('baseline_destination_exists',str(destination))
  moves.append((path.parent,destination))
 for run in legacy.glob('*'):
  destination=root/'data/baselines/runs/go'/run.name
  if destination.exists():raise Failure('baseline_destination_exists',str(destination))
 # Validate JSON before moving any files so malformed evidence cannot cause
 # a partially migrated tree.
 for path in legacy.rglob('*.json'):read(path)
 mapping={str(old):str(new) for old,new in moves}
 def relocate(value):
  if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
  if isinstance(value,list):return [relocate(v) for v in value]
  if isinstance(value,str):
   for old,new in mapping.items():
    if value==old or value.startswith(old+'/'):return new+value[len(old):]
  return value
 for old,new in moves:
  new.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(old),new)
  for path in new.rglob('*.json'):
   save(path,relocate(read(path)))
  result=read(new/'result.json')
  result['measurement_id']=old.parent.name+'/'+old.name
  result['original_record_path']=str(old/'result.json')
  save(new/'result.json',result)
 for run in sorted(legacy.glob('*')):
  if not run.is_dir():continue
  destination=root/'data/baselines/runs/go'/run.name
  destination.parent.mkdir(parents=True,exist_ok=True)
  if destination.exists():raise Failure('baseline_destination_exists',str(destination))
  for path in run.rglob('*.json'):save(path,relocate(read(path)))
  shutil.move(str(run),destination)
 if legacy.exists():legacy.rmdir()
 return mapping


def main():
 if sys.argv[1:]==['--migrate-storage']:
  print(json.dumps(migrate_storage(),indent=2));return
 cfg=config();run=ROOT/'data/baselines/runs/go'/('run-'+now().replace(':','').replace('+','_'))
 run.mkdir(parents=True)
 cases=sys.argv[1:] or read(ROOT/'catalog/studies/ownership-skills.json')['cases']
 results=[]
 for case in cases:
  print('Running '+case,flush=True)
  try:r=run_case(case,cfg,run)
  except Exception as e:r={'case':case,'status':'failed','error':str(e)}
  results.append(r);save(run/'summary.json',results)
  print(case+': '+r['status']+' '+r.get('error','')[:500],flush=True)
 print(str(run),flush=True)

if __name__=='__main__':main()
