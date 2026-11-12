"""Compact first views with complete versioned source/body retrieval."""
from copy import deepcopy
from .task_context import Archive,fingerprint
from .segmented_contract import items
from .common import Failure

SCHEMA='generation-interface-view-v1'
SMALL_BODY_CHARACTERS=4096


def declaration_view(files):
    """Retain imports/macros/bounds and trait defaults; omit ordinary fn bodies."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()));out={}
    for name,text in files.items():
        data=text.encode();ranges=[]
        def visit(node,in_trait=False):
            if node.type=='trait_item':in_trait=True
            if node.type=='function_item' and not in_trait:
                body=node.child_by_field_name('body')
                if body is not None:ranges.append((body.start_byte,body.end_byte))
                return
            # Macro token trees and their embedded syntax are retained exactly.
            if node.type=='macro_definition':return
            for child in node.named_children:visit(child,in_trait)
        visit(parser.parse(data).root_node)
        for start,end in sorted(ranges,reverse=True):data=data[:start]+b'{ /* exact body available through request_files */ }'+data[end:]
        out[name]=data.decode()
    return out


def compact(payload,state):
    out=deepcopy(payload);archive=Archive(state['bundle']['_context_archive'])
    versions=out['material_versions'];sources=versions.pop('sources',{})
    versions['source_catalog']=archive.put('catalog',sources)
    versions['source_paths']=list(state['bundle'].get('sources',{}))
    versions['source_catalog_instruction']='request_materials:[source_catalog] returns every original frozen source path/version; request_sources reads exact contents.'
    plan=state['partition'];out['partition']={k:plan[k] for k in ['version','policy','order','owner','boundaries'] if k in plan}
    out['partition']['units']={uid:{k:u[k] for k in ['id','name','members','dependencies','exports'] if k in u} for uid,u in plan['units'].items()}
    out['partition']['complete_catalog']=archive.put('catalog',plan)
    # Source equations/pages are never removed here. Only compiled Rust bodies
    # are initially withheld when the cumulative file has become substantial.
    hide=bool(state['completed']) and sum(map(len,state['files'].values()))>SMALL_BODY_CHARACTERS
    if hide:
        index=items(state['files'])
        out['current_files']={};out['code_pages']=[]
        out['dependency_declarations']=declaration_view(state['files'])
        out['dependency_interfaces']={n:[{**{k:r.get(k) for k in ['signature','file','scope','module_scope','kind','attributes']},
            **({'declaration':r['text']} if r['kind']!='function_item' else {})} for r in rows] for n,rows in index.items()}
        members=set(plan['units'][state['unit']]['members'])
        owned={r['rust_item'] for r in state['mapping'] if r['source'] in members and r.get('rust_item')}
        out['current_unit_items']={n:rows for n,rows in index.items() if n in owned}
        out['rust_items']={} # exact interfaces above replace duplicated metadata
    out['file_catalog']={name:{'lines':len(text.splitlines()),'characters':len(text),'sha256':fingerprint(text)} for name,text in state['files'].items()}
    out['generation_context']={'schema':SCHEMA,'dependency_bodies_initially_withheld':hide,'small_body_characters':SMALL_BODY_CHARACTERS,
        'protocol':'Complete source pages remain authoritative. Dependency interfaces retain bounds, macros, trait/default and impl declarations. request_files:[{path,code_version}] retrieves exact complete bodies; request_code_pages retrieves current excerpts. Read full files before replacing them. For new top-level definitions in an existing file prefer append_files:{"src/lib.rs":"new items only"} with state_version equal to controller_state.state_version; existing bytes are preserved. Use exact edits for changes to existing declarations/implementations, retrieving their bodies first. Shared-type or cross-unit repair still uses full repair context.'}
    return out


def expand_append(state,reply,current_version):
    if 'append_files' not in reply:return reply
    from .planning import validate_files
    additions=reply['append_files']
    if state.get('phase')!='generate' or reply.get('state_version')!=current_version:
        raise Failure('stale_patch','append_files is generation-only; copy controller_state.state_version from the current request, not code_version or a previous response',
                      {'required_field':'state_version','expected':current_version,'received':reply.get('state_version'),'phase':state.get('phase'),'instruction':'Re-read the current request before proposing a patch; no changes were applied.'})
    if not isinstance(additions,dict) or not additions:raise Failure('invalid_edit','append_files must contain existing Rust paths and nonempty appended items')
    validate_files(additions)
    touched=set(reply.get('files',{}))|{e.get('file') for e in reply.get('edits',[])}|set(reply.get('remove_files',[]))
    if set(additions)&touched:raise Failure('invalid_edit','Do not append and edit/replace/remove the same file in one transaction')
    files=dict(reply.get('files',{}))
    for name,text in additions.items():
        if name not in state['files'] or not name.endswith('.rs') or not isinstance(text,str) or not text.strip():
            raise Failure('invalid_edit','append_files requires an existing Rust file and nonempty source',name)
        files[name]=state['files'][name]+'\n'+text
    return {**reply,'files':files}
