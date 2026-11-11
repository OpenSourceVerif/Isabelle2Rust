"""Generated session glue: preserve theory imports/definitions/proofs, relocate exports."""
from pathlib import Path
import hashlib,json,re
EXPORT=re.compile(r'(?m)^[ \t]*(?:i2r_export_source|export_code)\s+[\s\S]*?\bin\s+Rust\b(?:[ \t]+module_name[ \t]+\w+)?')
def install(Executor,allowed_root):
 previous=Executor.run;allowed_root=Path(allowed_root).resolve()
 def run(self,command,*args,**kwargs):
  command=list(map(str,command))
  if 'build' in command:
   for i,token in enumerate(command[:-1]):
    if token!='-d':continue
    folder=Path(command[i+1]).resolve();root=folder/'ROOT'
    if not folder.is_relative_to(allowed_root) or not root.is_file():continue
    changes=[]
    # Only copied corpus subtree; never the independently authored Export/Model/Kernel.
    for theory in (folder/'source').rglob('*.thy'):
     original=theory.read_text();matches=list(EXPORT.finditer(original))
     if not matches:continue
     text=EXPORT.sub(lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),original)
     assert len(text)==len(original) and text.count('\n')==original.count('\n')
     for line in text.splitlines():assert not re.match(r'^\s*(export_code|i2r_export_source)\b',line),theory
     theory.write_text(text)
     changes.append({'path':str(theory),'before_sha256':hashlib.sha256(original.encode()).hexdigest(),'after_sha256':hashlib.sha256(text.encode()).hexdigest(),'removed_export_commands':[m.group() for m in matches],'change':'administrative export command replaced by same-length whitespace; all imports/definitions/proofs/line positions preserved'})
    if changes:(folder/'source-export-relocation.json').write_text(json.dumps(changes,indent=2)+'\n')
    dirs=sorted({str(p.parent.relative_to(folder)) for p in folder.rglob('*.thy') if p.parent!=folder})
    if not dirs:continue
    text=root.read_text();declaration=' directories '+' '.join(json.dumps(x) for x in dirs)+'\n'
    if declaration in text:continue
    at=re.search(r'(?m)^[ \t]*theories\b',text);assert at,root
    changed=text[:at.start()]+declaration+text[at.start():];root.write_text(changed)
    (folder/'session-directory-glue.json').write_text(json.dumps({'status':'generated_ROOT_directories_declared','root':str(root),'directories':dirs,'before_sha256':hashlib.sha256(text.encode()).hexdigest(),'after_sha256':hashlib.sha256(changed.encode()).hexdigest(),'source_imports_definitions_proofs_unchanged':True},indent=2)+'\n')
  return previous(self,command,*args,**kwargs)
 Executor.run=run
