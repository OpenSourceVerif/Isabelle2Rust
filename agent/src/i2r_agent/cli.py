from __future__ import annotations

import argparse
import json
import shutil
import sys

from .common import ROOT,Executor,Failure,config,read


def main():
    parser=argparse.ArgumentParser(prog='isabelle2rust-agent')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ['build','prepare']:
        p=sub.add_parser(command);p.add_argument('--project',required=True);p.add_argument('--output',required=True)
        p.add_argument('--config');p.add_argument('--numeric-mode',choices=['checked','arbitrary'])
        if command=='build':p.add_argument('--diagnostics-dir')
        p.add_argument('--json',action='store_true')
    sub.add_parser('doctor')
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if args.command=='serve':
        from .workbench import serve
        serve(args.port);return
    if args.command=='doctor':
        from .provider import credential
        cfg=config();status={k:str(v) for k,v in cfg['tools'].items()}
        try:status['model_credentials']='configured' if credential(cfg) else 'missing'
        except Failure:status['model_credentials']='missing'
        print(json.dumps(status,indent=2));return
    from .pipeline import build
    cfg=config(args.config or (str(__import__('pathlib').Path(args.project)/'agent.toml') if (__import__('pathlib').Path(args.project)/'agent.toml').exists() else None))
    if args.numeric_mode:
        if cfg.get('preprocessing',{}).get('mode')!='auto':raise Failure('invalid_config','--numeric-mode requires auto mode')
        cfg['preprocessing']['numeric_mode']=args.numeric_mode
    if args.command=='prepare':
        from .prepare import prepare
        result=prepare(args.project,args.output,cfg)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result['status']!='prepared':sys.exit(1)
        return
    result=build(args.project,args.output,cfg,args.diagnostics_dir,
                 progress=lambda r:print(f"{r['phase']}: {r['status']}",file=sys.stderr,flush=True))
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else f"{result['status']}: {result.get('output',result.get('error',''))}")
    if result['status']!='passed':sys.exit(1)


def study_main():
    parser=argparse.ArgumentParser(prog='i2r-study');sub=parser.add_subparsers(dest='command',required=True)
    for command in ['plan','run']:
        p=sub.add_parser(command);p.add_argument('config')
        if command=='run':
            p.add_argument('--id');p.add_argument('--resume',action='store_true');p.add_argument('--cases',nargs='+');p.add_argument('--variants',nargs='+')
    p=sub.add_parser('status');p.add_argument('id')
    p=sub.add_parser('export');p.add_argument('id');p.add_argument('--output',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    try:
        from .study import plan,run
        if args.command=='plan':result=plan(args.config)[1]
        elif args.command=='run':result=run(args.config,args.id,args.resume,args.cases,args.variants)
        elif args.command=='status':result=read(ROOT/'data/runs'/args.id/'summary.json')
        elif args.command=='export':
            result={'archive':shutil.make_archive(args.output,'gztar',ROOT/'data/runs',args.id)}
        else:
            from .workbench import serve
            serve(args.port);return
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if args.command=='run' and any(v!='passed' for v in result['results'].values()):sys.exit(1)
    except Failure as error:
        print(json.dumps({'error':error.code,'message':str(error)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
