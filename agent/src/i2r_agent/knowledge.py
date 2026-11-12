"""Source-grounded analysis and generation material; no test ABI in model input."""
from copy import deepcopy
import json
from pathlib import Path
from .common import ROOT, Failure, save, digest
from .context import source_context, bindings_for
from .export_contract import polymorphic_exports


def catalog(bundle):
    return {n['id']:n for p in bundle['programs'] for n in p['nodes']}


def material(bundle, extra=None):
    from .generation import intern_program
    nodes=catalog(bundle); entries=list(dict.fromkeys(e for p in bundle['programs'] for e in p['entries']))
    loaded=bundle.get('loaded_adapter') or bundle.get('base_adapter') or {}
    original=bundle.get('original_programs',bundle['programs'])
    result = {'entries':list(dict.fromkeys(e for p in original for e in p['entries'])),'active_entries':entries,'symbols':[{'id':n['id'],'kind':n['statement']['kind'],
        'signature':n['statement'].get('signature'),'dependencies':n['dependencies']} for n in nodes.values()],
        'thingol':intern_program(bundle['programs']),
        'sources':source_context(bundle),'source_catalog':[{k:item[k] for k in ['theory','path','available'] if k in item} for item in bundle.get('source_catalog',[])],
        'numeric_policy':bundle['numeric_policy'],'polymorphic_exports':polymorphic_exports({**bundle,'programs':original}),
        'active_bindings':bindings_for(bundle['programs'],loaded),'support':loaded.get('support',{}),
        'external_inventory':bundle.get('external_inventory',[]),
        'implementation_declarations':bundle.get('program_inventory',{}).get('implementation_declarations',[]),
        'analysis':bundle.get('semantic_analysis'), 'requested_material':extra or {},
        'reading_protocol':'The complete current Thingol graph, including every node body, is supplied once as a lossless shared representation. Follow $ref entries to table[N]. Request individual nodes for an expanded view or defining source ranges when needed. Original graphs remain archived. Testing scenarios/ABI/samples are not supplied.'}
    if 'source_model' in bundle:
        from .program_model import view
        result.pop('thingol')
        # Existing target coverage identifiers remain a compatibility obligation;
        # source entities and equations are independently extracted above it.
        result['backend_obligations'] = result.pop('symbols')
        for row in result['backend_obligations']:
            row.pop('signature', None)
        result['program_model'] = view(bundle)
        result['reading_protocol'] = 'Read source specifications and execution equations separately. program_model is an agent-owned view of Isabelle facts, not Thingol. Request exact typed entities, callers or source ranges. Backend obligations are compatibility IDs for existing mapping checks, not semantic definitions.'
    return result


def references(names):
    allowed={str(p.relative_to(ROOT/'references')):p for folder in ['semantic-adaptation','rust-generation']
             for p in (ROOT/'references'/folder/'references').glob('*.md')}
    from .repair_knowledge import CATALOG
    allowed[str(Path(CATALOG).relative_to('references'))]=ROOT/CATALOG
    unknown=set(names)-set(allowed)
    if unknown:raise Failure('unknown_reference','Choose a reference from the reference catalog',sorted(unknown))
    return {name:allowed[name].read_text() for name in names}


def requested(reply,bundle,files=None):
    from .task_context import validate_source_requests
    validate_source_requests(reply)
    if bundle.get('_context_archive'):
        from .task_context import read_material
        return read_material(reply,bundle,files)
    result={}
    graphs=list(bundle.get('original_programs',[]))
    if bundle.get('loaded_adapter',{}).get('before_target'):graphs.append(bundle['loaded_adapter']['before_target'])
    graphs+=bundle['programs']
    nodes={n['id']:n for graph in graphs for n in graph['nodes']}
    if reply.get('request_nodes'):
        missing=set(reply['request_nodes'])-set(nodes)
        if missing:raise Failure('unknown_source_symbol','Requested node IDs are not in the active or archived graphs',sorted(missing))
        result['nodes']=[nodes[x] for x in reply['request_nodes']]
    if reply.get('request_sources'):
        allowed={x['path']:Path(x['path']) for x in bundle.get('source_catalog',[]) if x.get('available')}
        rows=[]
        for request in reply['request_sources']:
            name=request['path']
            if name in bundle['sources']:text=bundle['sources'][name]
            elif name in allowed:text=allowed[name].read_text()
            else:raise Failure('unknown_source_path','Use an available source path',name)
            lines=text.splitlines();start=max(1,int(request.get('start_line',1)));end=min(len(lines),int(request.get('end_line',len(lines))))
            rows.append({'path':name,'start_line':start,'end_line':end,'text':'\n'.join(lines[start-1:end])})
        result['sources']=rows
    if reply.get('request_references'):result['references']=references(reply['request_references'])
    return result


def adapter_plan(reply,bundle):
    """Bridge only the runtime shape needed by the existing Isabelle loader."""
    reply=deepcopy(reply);adapter=reply.get('adapter',{});normalizations=[]
    if not isinstance(adapter,dict):raise Failure('invalid_adapter','adapter must be an object')
    for key in ['dependencies','build_dependencies','numeric_representation','sequence_representation','decisions','external_choices','notes']:
        if key not in reply and key in adapter:
            reply[key]=adapter.pop(key);normalizations.append('moved adapter.'+key+' to '+key)
    for key,default in [('imports',[]),('declarations',''),('rust_files',{}),('rust_root','')]:adapter.setdefault(key,default)
    validate_dependencies(reply.get('dependencies',{}),reply.get('build_dependencies',{}))
    return {'schema_version':3,'numeric_mode':bundle['numeric_policy']['mode'],'adapter':adapter,'protocol_normalizations':normalizations,
        'dependencies':reply.get('dependencies',{}),'build_dependencies':reply.get('build_dependencies',{}),
        'adaptation':{'numeric':reply.get('numeric_representation','model-selected'),
                      'sequence':reply.get('sequence_representation','model-selected'),'decisions':reply.get('decisions',[])},
        'boundaries':reply.get('external_choices',[]),'notes':reply.get('notes','')}


def validate_dependencies(dependencies,build_dependencies=None):
    from .planning import manifest
    try:manifest(dependencies,transport='none',build_dependencies=build_dependencies)
    except Failure as error:
        raise Failure('invalid_dependencies',str(error)+'; versions require a leading =, e.g. =0.4.6, or an object with version, features and optional default-features.',
            {'dependencies':dependencies,'build_dependencies':build_dependencies}) from error


def apply_files(previous,reply,diagnostics=None):
    from .planning import validate_files,normalize_files
    if reply.get('base_code_version'):
        from .task_context import fingerprint
        if reply['base_code_version'] not in {fingerprint(previous),'code-'+fingerprint(previous)}:
            raise Failure('stale_patch','Patch targets an obsolete code version; reread current files')
    files=deepcopy(previous);incoming=reply.get('files',{})
    validate_files(incoming);files.update(incoming)
    edits=reply.get('edits',[])
    if not isinstance(edits,list):raise Failure('invalid_edit','edits must be an array')
    for edit in edits:
        if not isinstance(edit,dict) or not {'file','old','new'}<=set(edit):raise Failure('invalid_edit','Each edit needs file, old and new')
        name,old,new=edit['file'],edit['old'],edit['new']
        if not all(isinstance(x,str) for x in (name,old,new)):
            raise Failure('invalid_edit','file, old and new must be strings',edit)
        if name not in files:
            raise Failure('unknown_edit_file','Edit target does not exist; choose an editable file or use files to create it',
                {'file':name,'editable_files':sorted(files)})
        if not old:raise Failure('invalid_edit','old must be nonempty',edit)
        matches=files[name].count(old)
        if matches!=1:
            raise Failure('edit_text_mismatch','Edit target exists, but old text must match exactly once',
                {'file':name,'matches':matches,'old':old,'instruction':'Read the current file; use unique exact text or return its complete replacement.'})
        files[name]=files[name].replace(old,new,1)
    normalized,changes=normalize_files(files)
    if changes and diagnostics:save(diagnostics,{'normalizations':changes})
    return normalized


def correspondence(bundle,files,mapping):
    from .export_contract import check_exports
    if not isinstance(mapping,list):raise Failure('plan_contract_failed','mapping must be an array')
    original=bundle.get('original_programs',bundle['programs'])
    required=set(catalog(bundle))|{e for graph in original for e in graph['entries']};provided={x['source'] for x in mapping}
    missing=required-provided
    if missing:raise Failure('plan_contract_failed','Give realizations for remaining active nodes; existing mapping is retained',{
        'missing':sorted(missing),
        'repair_protocol':{'action':'generate','mapping':[{'source':sorted(missing)[0],'rust':'actual existing Rust item, trait bound, type or inline realization'}]},
        'instruction':'Return mapping (exact key), one record for EACH missing ID. Existing code need not change for a traceability-only omission. A class may map to a justified trait bound; a type may map to its actual representation. Rust edits, comments, mapping_changes/mapping_additions and Isabelle declarations do not update this table.'})
    if any(not x.get('rust') for x in mapping):raise Failure('plan_contract_failed','Each correspondence needs a Rust realization')
    check_exports({**bundle,'programs':original},files,mapping)
    return {'status':'passed','active_nodes':len(required),'scope':'Traceability and syntactic generic API check; not equivalence proof'}


def merge_mapping(previous,incoming,remove=None):
    if incoming is not None and (not isinstance(incoming,list) or any(
        not isinstance(row,dict) or not isinstance(row.get('source'),str) or not isinstance(row.get('rust'),str)
        or not row['source'] or not row['rust'] for row in incoming)):
        raise Failure('invalid_mapping_field','mapping must be a list of {source: "source ID", rust: "actual realization"}; rust_item is optional for non-generic realizations.')
    if remove is not None and (not isinstance(remove,list) or any(not isinstance(x,str) for x in remove)):
        raise Failure('invalid_mapping_field','remove_mapping must be a list of existing source IDs')
    remove=set(remove or [])
    unknown=remove-{row['source'] for row in previous}
    conflict=remove & {row['source'] for row in (incoming or [])}
    if unknown or conflict:
        raise Failure('invalid_mapping_field','Remove existing IDs only; do not both remove and update an ID',
            {'unknown_removals':sorted(unknown),'conflicting_updates':sorted(conflict)})
    return list({row['source']:row for row in previous+(incoming or []) if row['source'] not in remove}.values())
