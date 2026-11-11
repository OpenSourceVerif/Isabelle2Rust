"""Live Isabelle Haskell/Scala/SML baselines in the shared baseline registry."""
from pathlib import Path
import argparse
import hashlib
import re
import shlex
import shutil

from .common import ROOT, Executor, Failure, config, digest, now, read, save
from .baselines import fingerprint, cached_outputs, measure_once, valid_record, language_artifacts
from .preprocessing import project_info, isabelle_command
from .performance import benchmark
from .validation import execute
from . import suites

TARGETS = {'haskell': 'Haskell', 'scala': 'Scala', 'sml': 'SML'}
HASKELL_DRIVER = '''module Main where
import qualified Candidate as C
import Control.DeepSeq (force)
import Control.Exception (evaluate)
import Control.Monad (forM_)
import GHC.Clock (getMonotonicTimeNSec)
import System.Environment (getArgs)
import System.IO (hPutStrLn, stderr)
main :: IO ()
main = do
  args <- getArgs
  contents <- getContents
  forM_ (lines contents) $ \\line -> do
    input <- evaluate (force (map (C.nat_of_integer . read) (words line)))
    output <- if "--i2r-benchmark" `elem` args then do
      prepared <- evaluate (force (C.kernel_prepare input))
      start <- getMonotonicTimeNSec
      result <- evaluate (force (C.kernel_run prepared))
      end <- getMonotonicTimeNSec
      hPutStrLn stderr ("I2R_KERNEL_NS " ++ show (end-start))
      pure (C.kernel_encode result)
      else pure (C.observe input)
    putStrLn (unwords (map (show . C.integer_of_nat) output))
'''
SCALA_DRIVER = '''object Main {
  def main(args: Array[String]): Unit = {
    val measuring = args.contains("--i2r-benchmark")
    for (line <- scala.io.Source.stdin.getLines()) {
      val input = line.split("\\\\s+").filter(_.nonEmpty).toList.map(s => Candidate.nat_of_integer(BigInt(s)))
      val output = if (measuring) {
        val prepared = Candidate.kernel_prepare(input)
        val start = System.nanoTime()
        val result = Candidate.kernel_run(prepared)
        val elapsed = System.nanoTime() - start
        System.err.println("I2R_KERNEL_NS " + elapsed)
        Candidate.kernel_encode(result)
      } else Candidate.observe(input)
      println(output.map(n => Candidate.integer_of_nat(n).toString).mkString(" "))
    }
  }
}
'''
CLOCK = '''#include <time.h>
static struct timespec started;
void i2r_start(void) { clock_gettime(CLOCK_MONOTONIC, &started); }
double i2r_stop(void) {
  struct timespec ended; clock_gettime(CLOCK_MONOTONIC, &ended);
  return (double)(ended.tv_sec-started.tv_sec)*1000000000.0 + (ended.tv_nsec-started.tv_nsec);
}
'''
SML_DRIVER = '''structure Main = struct
fun main () = let
  val library = Foreign.loadLibrary "@CLOCK@"
  val start = Foreign.buildCall0 (Foreign.getSymbol library "i2r_start", (), Foreign.cVoid)
  val stop = Foreign.buildCall0 (Foreign.getSymbol library "i2r_stop", (), Foreign.cDouble)
  val measuring = List.exists (fn s => s = "--i2r-benchmark") (CommandLine.arguments ())
  fun loop () = case TextIO.inputLine TextIO.stdIn of NONE => () | SOME line => let
    val input = List.map (fn s => Candidate.nat_of_integer (valOf (IntInf.fromString s))) (String.tokens Char.isSpace line)
    val output = if measuring then let
      val prepared = Candidate.kernel_prepare input
      val _ = start ()
      val result = Candidate.kernel_run prepared
      val elapsed = stop ()
      val _ = TextIO.output (TextIO.stdErr, "I2R_KERNEL_NS " ^ LargeInt.toString (Real.toLargeInt IEEEReal.TO_NEAREST elapsed) ^ "\\n")
      in Candidate.kernel_encode result end else Candidate.observe input
    val _ = print (String.concatWith " " (List.map (IntInf.toString o Candidate.integer_of_nat) output) ^ "\\n")
    in loop () end
  in loop () end
end;
'''


def haskell_strictness(source):
    """Derive structural forcing only; retain the untouched export alongside it."""
    source = '{-# LANGUAGE DeriveGeneric, DeriveAnyClass #-}\n' + source
    source = source.replace('import qualified Prelude;',
        'import qualified Prelude;\nimport qualified GHC.Generics;\nimport qualified Control.DeepSeq;')
    return re.sub(r'((?:^|\n)(?:data|newtype)\s+[^;]+);',
                  r'\1 deriving (GHC.Generics.Generic, Control.DeepSeq.NFData);', source)


def baseline_for(case):
    project = ROOT/'catalog/cases'/case/'testing'
    if not project.exists():project = project.parent
    sources = {p.name:digest(p) for p in project.glob('*.thy')}
    if not sources:raise Failure('baseline_sources_missing',str(project))
    candidates = []
    for p in (ROOT/'data/baselines').glob(case+'-*/baseline.json'):
        b = read(p)
        if not all(b['identity']['sources'].get(k)==v for k,v in sources.items()):continue
        external = {k:v for k,v in b['identity']['sources'].items() if Path(k).is_absolute()}
        if not all(Path(k).is_file() and digest(k)==v for k,v in external.items()):continue
        if valid_record(b):candidates.append(b)
    if not candidates:raise Failure('baseline_missing','No exact reference sources for '+case)
    return project,max(candidates,key=lambda b:b['created_at'])


def export_targets(case,project,base,cfg,run):
    work = ROOT/'data/baselines'/base['id']/'build'/run.name
    work.mkdir(parents=True,exist_ok=True)
    home=Path(cfg['tools']['isabelle']).resolve().parents[1]
    tool_files=list((home/'src/Tools/Code').glob('*.ML'))+list((home/'src/HOL').glob('Code_*.thy'))+list((home/'src/HOL/Library').glob('Code_*.thy'))
    key={'sources':base['identity']['sources'],'runner':digest(__file__),
         'tools':cfg['tools'],'code_generator_sources':{str(p):digest(p) for p in tool_files}}
    if (work/'export.json').exists():
        record=read(work/'export.json')
        if record.get('identity')!=key:raise Failure('native_export_identity_changed','Use a new run ID: '+str(work))
        if all(Path(p).is_file() and digest(p)==h for p,h in record['hashes'].items()):return work/'exported'
        raise Failure('native_export_changed',str(work))
    for p in project.glob('*.thy'):shutil.copy2(p,work/p.name)
    p=work/'Export.thy'
    source=p.read_text().replace('"I2R_Agent.Agent_Export"','"HOL-Library.Code_Target_Nat"')
    source,n=re.subn(r'export_code\s+(.*?)\s+in Rust_Agent module_name Candidate',
        lambda m:'\n'.join('export_code '+m[1]+' nat_of_integer integer_of_nat in '+t+' module_name Candidate'+(' (case_insensitive)' if t=='Scala' else '') for t in TARGETS.values()),source,flags=re.S)
    if n!=1:raise Failure('native_export_layout','Expected one Candidate export')
    p.write_text(source)
    theories,sessions=project_info(project)
    session='I2R_Native_'+case.replace('-','_')+'_'+fingerprint({'run':run.name,'sources':base['identity']['sources']})[:10]
    (work/'ROOT').write_text(f'session {session} = HOL +\n options [document=false]\n sessions '+ ' '.join('"'+s+'"' for s in sorted(set(sessions)|{'HOL-Library'}))+'\n theories '+ ' '.join(theories)+'\n export_files (in "exported") [2] "*:code/**"\n')
    ex=Executor(work/'logs')
    command=isabelle_command(cfg,'build','-e','-j','1','-o','threads=2','-d',cfg['tools']['afp'],'-d',work,session)
    record=ex.run(command,timeout=cfg['budgets']['build_seconds'])
    if any(digest(p)!=h for p,h in key['code_generator_sources'].items()):raise Failure('native_tool_sources_changed',str(home))
    save(work/'export.json',{'identity':key,'execution':record,'hashes':{str(p):digest(p) for p in (work/'exported').rglob('*') if p.is_file()}})
    return work/'exported'


def shell_launcher(path,argv):
    path.write_text('#!/bin/sh\nexec '+shlex.join(map(str,argv))+' "$@"\n');path.chmod(0o755)


def compile_target(language,exported,work,cfg,ex):
    isabelle=cfg['tools']['isabelle'];binary=work/'reference'
    if language=='haskell':
        ghc=shutil.which('ghc') or '/opt/homebrew/bin/ghc'
        version=ex.run([ghc,'--numeric-version'])
        source=work/'Candidate.raw.hs';shutil.copy2(next(exported.rglob('Candidate.hs')),source)
        (work/'Candidate.hs').write_text(haskell_strictness(source.read_text()))
        (work/'Main.hs').write_text(HASKELL_DRIVER)
        ex.run([ghc,'-O2','-fno-full-laziness','-fno-cse','-i'+str(work),'-outputdir',work/'objects','-o',binary,work/'Main.hs'],cwd=work,timeout=300)
        timer='GHC monotonic nanoseconds; prepared input and kernel result forced to normal form; forcing traversal included in kernel time'
    elif language=='scala':
        version=ex.run([isabelle,'scalac','-version'])
        options_record=ex.run([isabelle,'getenv','-b','ISABELLE_SCALAC_OPTIONS'])
        options=shlex.split(Path(options_record['stdout']).read_text().strip())
        source=work/'Candidate.scala';shutil.copy2(next(exported.glob('*.scala')),source)
        (work/'Main.scala').write_text(SCALA_DRIVER)
        classes=work/'classes';classes.mkdir(exist_ok=True)
        ex.run([isabelle,'scalac',*options,'-d',classes,source,work/'Main.scala'],cwd=work,timeout=300)
        shell_launcher(binary,[isabelle,'scala','-J-Xss16m','-classpath',classes,'Main'])
        timer='JVM System.nanoTime; JVM startup excluded; JIT and GC during kernel_run included'
    else:
        env=ex.run([isabelle,'getenv','-b','ML_HOME'])
        poly=Path(Path(env['stdout']).read_text().strip())/'poly'
        version=ex.run([poly,'-v'])
        source=work/'Candidate.ML';shutil.copy2(next(exported.glob('*.ML')),source)
        clock=work/'kernel_clock.dylib';(work/'kernel_clock.c').write_text(CLOCK)
        ex.run(['cc','-dynamiclib','-O2','-o',clock,work/'kernel_clock.c'])
        (work/'Main.ML').write_text(SML_DRIVER.replace('@CLOCK@',str(clock)))
        heap=work/'compiled.heap'
        loader='use "'+str(source)+'"; use "'+str(work/'Main.ML')+'"; PolyML.SaveState.saveState "'+str(heap)+'";'
        ex.run([poly,'--error-exit','-q','--eval',loader],cwd=work,timeout=300)
        shell_launcher(binary,[poly,'--error-exit','-q','--eval','val _ = PolyML.SaveState.loadState "'+str(heap)+'"; val _ = Main.main (); val _ = OS.Process.exit OS.Process.success;'])
        timer='Poly/ML with C CLOCK_MONOTONIC via FFI; ordinary timer-call/FFI overhead included'
    return source,binary,version,timer


def test_and_measure(case,language,base,binary,cfg,ex,work,timer):
    seed=cfg['testing']['seed']+int(hashlib.sha256(case.encode()).hexdigest()[:6],16)
    regressions={}
    for p in (ROOT/'data/runs').glob('*/inputs/'+case+'/regressions.json'):
        for r in read(p):
            if suites.domain(case,r['input']):regressions[fingerprint(r['input'])]=r['input']
    groups={'fixed':suites.fixed(case),'regression':list(regressions.values()),
            'generated':suites.generate(case,cfg['testing']['random_cases'],seed),
            'final':suites.generate(case,cfg['testing']['final_cases'],seed+1000003)}
    checks=[]
    for kind,inputs in groups.items():
        save(work/(kind+'-inputs.json'),inputs)
        expected=cached_outputs(case,inputs,base['references'],ex,cfg['testing']['process_timeout'])['ocaml']['outputs']
        for label,args in [('observer',()),('kernel',('--i2r-benchmark',))]:
            actual=execute(binary,inputs,ex,cfg['testing']['process_timeout'],args)
            ok=actual['status']=='passed' and actual['outputs']==expected
            checks.append({'suite':kind,'path':label,'count':len(inputs),'status':'passed' if ok else 'failed','execution':actual['record']})
            save(work/'checks.json',checks)
            if not ok:raise Failure('native_behavior_failed',kind+' '+label,actual)
    workload=suites.scoped_performance_input(case,cfg['performance'].get('input_bits',128))
    expected=cached_outputs(case,[workload],base['references'],ex,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
    # Use compatible existing reference options/timestamps; do not retime them
    # just because unrelated configuration metadata has gained new keys.
    directory=Path(base['references']['ocaml']['baseline_record']).parent
    measurements=[read(p) for p in (directory/'measurements').glob('*.json')]
    matching=[m for m in measurements if m.get('scope')=='kernel' and m['workload']==workload and
              all(m['protocol']['options'].get(k)==cfg['performance'][k] for k in ['samples','warmups','iterations'])]
    if cfg['performance'].get('protocol')=='kernel-v2':matching=[]
    reference=max(matching,key=lambda m:m['measured_at']) if matching else measure_once(base,workload,expected,cfg,ex)
    measurement_cfg={**cfg,'performance':reference['protocol']['options']}
    perf=benchmark({language:str(binary)},workload,expected,measurement_cfg,ex,work)
    if perf['protocol']['version']=='kernel-v1':perf['protocol']['timer']=timer
    perf.update(measured_at=now(),acquisition='measured_once',origin=str(work/'performance.json'))
    save(work/'performance.json',perf)
    return checks,perf,reference['record_path']


def run_case(case,languages,cfg,run,resume=False):
    project,base=baseline_for(case);results=[]
    try:exported=export_targets(case,project,base,cfg,run);export_error=None
    except Exception as e:exported=None;export_error=e
    for language in languages:
        work=language_artifacts(base['id'],language,ROOT)/run.name;work.mkdir(parents=True,exist_ok=True)
        path=work/'result.json'
        if resume and path.exists() and read(path)['status']=='passed':
            previous=read(path)
            if export_error:raise export_error
            if previous['identity']['runner']!=digest(__file__) or previous['identity']['config']!=cfg:
                raise Failure('native_resume_identity_changed','Use a new run ID: '+str(path))
            if all(Path(p).is_file() and digest(p)==h for p,h in previous['artifact_hashes'].items()):
                results.append(previous);continue
            raise Failure('native_artifact_changed',str(path))
        result={'case':case,'language':language,'status':'running','started_at':now(),
                'baseline_id':base['id'],'measurement_id':run.name+'/'+case+'/'+language,
                'identity':{'sources':base['identity']['sources'],'runner':digest(__file__),'config':cfg,
                            'target':TARGETS[language],'protocol':'kernel-v1'}}
        if path.exists():save(work/'history'/('result-'+fingerprint(read(path))[:16]+'.json'),read(path))
        save(path,result);ex=Executor(work/'logs')
        try:
            if export_error:raise export_error
            result['identity']['export']=read(exported.parent/'export.json')
            source,binary,version,timer=compile_target(language,exported,work,cfg,ex)
            result['reference']={'binary':str(binary),'binary_sha256':digest(binary),'source':str(source),'sha256':digest(source),'timing_protocol':'kernel-v1'}
            result['identity']['compiler_version']=Path(version['stdout']).read_text()+Path(version['stderr']).read_text()
            save(path,result)
            checks,perf,reference=test_and_measure(case,language,base,binary,cfg,ex,work,timer)
            result.update(status='passed',checks=checks,performance=perf,reference_measurement=reference,
                          artifact_hashes={str(p):digest(p) for p in work.rglob('*') if p.is_file() and
                                           'logs' not in p.relative_to(work).parts and p.name!='result.json'})
        except Exception as e:
            result.update(status='failed',error=str(e),error_code=getattr(e,'code',type(e).__name__),evidence=getattr(e,'evidence',None))
        result['finished_at']=now();save(path,result);results.append(result)
        print(case+' '+language+': '+result['status']+' '+result.get('error','')[:300],flush=True)
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cases',nargs='+')
    parser.add_argument('--languages',nargs='+',choices=TARGETS,default=list(TARGETS))
    parser.add_argument('--run-id',default='run-'+now().replace(':','').replace('+','_'))
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();cfg=config()
    run=ROOT/'data/baselines/runs/native'/args.run_id;run.mkdir(parents=True,exist_ok=args.resume)
    cases=args.cases or read(ROOT/'catalog/studies/ownership-skills.json')['cases']
    results=read(run/'summary.json') if args.resume and (run/'summary.json').exists() else []
    for case in cases:
        print('Running '+case,flush=True)
        fresh=run_case(case,args.languages,cfg,run,args.resume)
        keys={(r['case'],r['language']) for r in fresh}
        results=[r for r in results if (r['case'],r['language']) not in keys]+fresh
        save(run/'summary.json',results)
    print(str(run),flush=True)

if __name__=='__main__':main()
