"""Bounded review views and conservative exemption for independent additions.

This is syntax analysis, not Rust name resolution. Imports/impls/macros and
changed existing declarations still use the conservative invalidation fallback.
"""
import re
from .rust_index import build
from .segmented_contract import items,validate_item
from .segmented_context import code_pages
from .task_context import fingerprint
from .common import Failure

WHOLE={'whole_review','performance_review'}


def body_change_impact(state,files,mapping,cfg,changed_items):
    """Localize existing free-function body edits, including unfinished owners.

    Signatures, attributes, methods and ambiguous locations retain the global
    fallback. The caller separately checks imports, macros and local impl effects.
    Both old and new conservative review closures are checked, so shared helpers,
    indirect function values and simultaneous caller edits remain dependencies.
    """
    old=items(state['files']);new=items(files);local=set()
    for name in changed_items:
        a=old.get(name,[]);b=new.get(name,[])
        if len(a)!=1 or len(b)!=1:continue
        a,b=a[0],b[0]
        if (a['kind']==b['kind']=='function_item' and
                not a['scope'] and not b['scope'] and
                not a['lexical_scope'] and not b['lexical_scope'] and
                all(a.get(k)==b.get(k) for k in ['file','signature','attributes'])):
            local.add(name)
    affected=set()
    if not local:return local,affected
    for uid in state['completed']:
        sources=set(state['partition']['units'][uid]['members'])
        # view supplies transitive Rust references and conservative macro fallback.
        for snapshot,index in [({**state,'unit':uid,'phase':'refine'},old),
                               ({**state,'unit':uid,'phase':'refine','files':files,'mapping':mapping},new)]:
            _,_,ranges=view(snapshot,sources,cfg)
            if any(any(line in ranges.get(row['file'],set())
                       for line in range(row['start_line'],row['end_line']+1))
                   for name in local for row in index[name]):
                affected.add(uid);break
    return local,affected


def independent_additions_removed(old_files,new_files):
    """Remove only fresh unreferenced top-level declarations for context comparison."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()))
    # Built-in derives only implement traits for their fresh local type. Custom
    # derives can emit arbitrary items, so never give them this exemption.
    builtin_derives={'Debug','Clone','Copy','PartialEq','Eq','PartialOrd','Ord','Hash','Default'}
    derive_shadowed=False
    for text in new_files.values():
        data=text.encode();pending=[parser.parse(data).root_node]
        while pending:
            node=pending.pop();pending.extend(node.children)
            fragment=data[node.start_byte:node.end_byte].decode()
            if node.type in {'macro_definition','macro_invocation','mod_item','extern_crate_declaration','inner_attribute_item'}:
                derive_shadowed=True
            if node.type=='attribute_item' and not re.match(r'#\s*\[\s*(?:derive|allow|warn|deny|forbid)\s*\(',fragment):
                derive_shadowed=True
            if node.type=='attribute_item' and re.match(r'#\s*\[\s*derive\b',fragment):
                match=re.fullmatch(r'#\s*\[\s*derive\s*\(([^()]*)\)\s*\]',fragment)
                if not match or any(n.strip() not in builtin_derives for n in match[1].split(',') if n.strip()):
                    derive_shadowed=True
            if node.type=='use_declaration' and ('*' in fragment or builtin_derives & set(re.findall(r'\b\w+\b',fragment))):
                derive_shadowed=True

    def inert_attribute(node,data):
        text=data[node.start_byte:node.end_byte].decode()
        match=re.fullmatch(r'#\s*\[\s*derive\s*\(([^()]*)\)\s*\]',text)
        if match and not derive_shadowed:
            names=[n.strip() for n in match[1].split(',') if n.strip()]
            return bool(names) and all(n in builtin_derives for n in names)
        # Lint levels do not emit declarations or alter dispatch. Keep cfg,
        # cfg_attr, repr and arbitrary attribute macros conservative.
        return bool(re.fullmatch(r'#\s*\[\s*(?:allow|warn|deny|forbid)\s*\(\s*[A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)*\s*,?\s*\)\s*\]',text))

    def attached_start(node,data,allow_attributes=True):
        # Rust outer doc comments are siblings, not children of the declaration.
        # Exclude them with an exempt item; leave inner/module documentation and
        # semantic attributes conservative. Ordinary comments alone do not move
        # the boundary, preserving unrelated trailing comments on older items.
        start=node.start_byte;previous=node.prev_named_sibling
        while previous is not None and previous.type in {'attribute_item','line_comment','block_comment'}:
            text=data[previous.start_byte:previous.end_byte].decode()
            if previous.type=='attribute_item':
                if not allow_attributes or not inert_attribute(previous,data):return None
                start=previous.start_byte
            elif text.startswith(('//!','/*!')):
                break
            elif (text.startswith('///') and not text.startswith('////') or
                  text.startswith('/**') and not text.startswith('/***')):
                start=previous.start_byte
            previous=previous.prev_named_sibling
        return start
    # Include identifiers in imports, macros and local scopes too. False positives
    # retain the conservative check; never guess resolved Rust symbol identity.
    identifiers=set();old_opaque=False
    for text in old_files.values():
        data=text.encode();root=parser.parse(data).root_node
        if root.has_error:return dict(new_files),[]
        pending=[root]
        while pending:
            node=pending.pop();pending.extend(node.children)
            if node.type in {'macro_definition','macro_invocation','mod_item','inner_attribute_item'}:
                old_opaque=True
            if node.type in {'identifier','type_identifier','field_identifier'}:
                identifiers.add(data[node.start_byte:node.end_byte].decode())
    result=dict(new_files);exempt=[]
    allowed={'function_item','type_item','struct_item','enum_item','trait_item','const_item','static_item'}
    for path,text in new_files.items():
        if path not in old_files or not path.endswith('.rs'):continue
        data=text.encode();tree=parser.parse(data)
        if tree.root_node.has_error:continue
        cuts=[]
        for node in tree.root_node.named_children:
            if node.type not in allowed:continue
            name=node.child_by_field_name('name')
            if name is None:continue
            label=data[name.start_byte:name.end_byte].decode()
            if label in identifiers:continue
            # Attributes can invoke procedural macros/derive; nested impls and
            # macros can change existing dispatch even in an unused function.
            start=attached_start(node,data)
            if start is None:continue
            pending=list(node.children);hazard=False
            while pending:
                child=pending.pop();pending.extend(child.children)
                if child.type=='attribute_item':
                    if not inert_attribute(child,data):hazard=True
                elif child.type in {'impl_item','macro_definition','macro_invocation','inner_attribute_item','use_declaration'}:hazard=True
            if hazard:continue
            cuts.append((start,node.end_byte));exempt.append({'file':path,'name':label,'kind':node.type})
        # A fresh inline module cannot affect existing code when its name is
        # absent from all old syntax and its entire body contains no impls,
        # macros, attributes or out-of-line modules. Imports inside that new
        # lexical scope do not alter old name resolution. Keep opaque old
        # macros and every potentially global extension conservative.
        if not old_opaque:
            for node in tree.root_node.named_children:
                if node.type!='mod_item' or node.child_by_field_name('body') is None:continue
                name=node.child_by_field_name('name')
                if name is None:continue
                label=data[name.start_byte:name.end_byte].decode()
                if label in identifiers:continue
                start=attached_start(node,data,allow_attributes=False)
                if start is None:continue
                pending=list(node.children);hazard=False
                while pending:
                    child=pending.pop();pending.extend(child.children)
                    if child.type in {'impl_item','macro_definition','macro_invocation','attribute_item','inner_attribute_item','extern_crate_declaration'}:hazard=True
                    if child.type=='mod_item' and child.child_by_field_name('body') is None:hazard=True
                if hazard:continue
                cuts.append((start,node.end_byte))
                exempt.append({'file':path,'name':label,'kind':'mod_item'})
        # A new local trait cannot affect old bounds when its name was absent.
        # Its impls can still add methods/associated names to existing types:
        # exempt them only if every such name is absent from old syntax too.
        # Existing traits/inherent impls, opaque macros/modules and attributes
        # retain the fallback. Never infer independence from the target type.
        fresh_traits={r['name'] for r in exempt if r['file']==path and r['kind']=='trait_item'}
        if not old_opaque and not derive_shadowed:
            for node in tree.root_node.named_children:
                if node.type!='impl_item':continue
                trait=node.child_by_field_name('trait')
                if trait is None or trait.type!='type_identifier':continue
                trait_name=data[trait.start_byte:trait.end_byte].decode()
                if trait_name not in fresh_traits:continue
                definition=next(n for n in tree.root_node.named_children if n.type=='trait_item' and
                                data[n.child_by_field_name('name').start_byte:n.child_by_field_name('name').end_byte].decode()==trait_name)
                bounds=definition.child_by_field_name('bounds')
                if bounds is not None and re.sub(r'\s+','',data[bounds.start_byte:bounds.end_byte].decode())!=':Sized':continue
                start=attached_start(node,data,allow_attributes=False)
                if start is None:continue
                # Include default methods and associated names from the trait,
                # even when the impl inherits them without spelling them again.
                pending=list(node.children)+list(definition.children);hazard=False
                while pending:
                    child=pending.pop();pending.extend(child.children)
                    if child.type in {'impl_item','macro_definition','macro_invocation','attribute_item','inner_attribute_item','use_declaration','mod_item'}:hazard=True
                    if child.type in {'function_item','function_signature_item','const_item','type_item'}:
                        name=child.child_by_field_name('name')
                        if name is not None and data[name.start_byte:name.end_byte].decode() in identifiers:hazard=True
                if hazard:continue
                cuts.append((start,node.end_byte))
                exempt.append({'file':path,'name':trait_name,'kind':'impl_item'})
        for a,b in sorted(cuts,reverse=True):data=data[:a]+data[b:]
        result[path]=data.decode()
    return result,exempt


def view(state,source_ids,cfg):
    """Full mapped owners plus conservative lexical dependency closure, original lines."""
    files=state['files']
    if state.get('phase') in WHOLE or state.get('unit') is None:
        return files,code_pages(files,cfg['segmented']['source_page_characters']),None
    index=items(files);parsed=build(files);rows=parsed['items'];selected=[]
    for mapping in state['mapping']:
        if mapping['source'] in source_ids and mapping.get('rust_item'):
            row=validate_item(index,mapping)
            if row.get('kind')!='external_type':selected.append(row)
    # Ambiguous references include every matching declaration. Include enclosing
    # impl/trait/type and implementation blocks for selected types/traits.
    changed=True
    while changed:
        before=len(selected)
        names={n for row in selected for n in row.get('references',[])}
        names.update(row['name'] for row in selected if row.get('name'))
        for row in rows:
            related=(row.get('name') in names or
                     row['kind']=='impl_item' and bool(names & set(re.findall(r'\b[A-Za-z_]\w*\b',row['signature']))) or
                     any(row['file']==s['file'] and row['start_line']<=s['start_line'] and row['end_line']>=s['end_line'] for s in selected))
            if related and row not in selected:selected.append(row)
        changed=len(selected)!=before
    ranges={}
    for row in selected:
        start=row['start_line']-len(row.get('attributes',[]))
        ranges.setdefault(row['file'],set()).update(range(max(1,start),row['end_line']+1))
    # Imports, module/impl context and macros are ambient semantic context. When
    # syntax cannot isolate them safely, include the file in the review view.
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()))
    for path,text in files.items():
        if not path.endswith('.rs'):continue
        data=text.encode();tree=parser.parse(data);pending=[tree.root_node]
        while pending:
            node=pending.pop();pending.extend(node.children)
            if node.type in {'use_declaration','inner_attribute_item'}:
                ranges.setdefault(path,set()).update(range(node.start_point.row+1,node.end_point.row+2))
            if node.type in {'mod_item','macro_definition','macro_invocation'} or tree.root_node.has_error:
                ranges[path]=set(range(1,len(text.splitlines())+1));break
    excerpts={p:'\n'.join(line if i in ranges[p] else '' for i,line in enumerate(text.splitlines(),1)).rstrip()+'\n'
              for p,text in files.items() if p in ranges}
    return excerpts,code_pages(excerpts,cfg['segmented']['source_page_characters']),ranges


def ambient_identity(files):
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()));result=[]
    for path,text in sorted(files.items()):
        if not path.endswith('.rs'):continue
        data=text.encode();todo=[parser.parse(data).root_node]
        while todo:
            n=todo.pop()
            if n.type in {'impl_item','use_declaration','mod_item','macro_definition','macro_invocation','inner_attribute_item','attribute_item'}:
                result.append((path,n.type,data[n.start_byte:n.end_byte].decode()))
            else:todo.extend(reversed(n.children))
    return result


def review_tokens(files):
    """Ignore layout padding without erasing whitespace inside Rust literals."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()));result={}
    for path,text in files.items():
        data=text.encode();root=parser.parse(data).root_node
        if root.has_error:result[path]=text;continue
        tokens=[];pending=[root]
        while pending:
            node=pending.pop()
            if node.children:pending.extend(reversed(node.children))
            else:tokens.append((node.type,data[node.start_byte:node.end_byte].decode()))
        result[path]=tokens
    return result


def review_identity(state,source_ids,review_files,*,legacy=False,schema=4):
    # Excerpt padding records original line numbers, not semantics. Appending or
    # lengthening an unrelated function must not hide a duplicate schedule.
    context={'unit':state.get('unit'),'files':review_tokens(review_files),'config':state['rust_config'],
                          'ambient':ambient_identity(state['files']),
                          'sources':{n:state['bundle']['source_model']['entities'][n] for n in sorted(source_ids)},
                          'mapping':[r for r in state['mapping'] if r['source'] in source_ids]}
    if not legacy:
        # Invalidation propagates through transitive source dependencies. The
        # duplicate guard must include their contracts as well, even when the
        # Rust text did not change (e.g. a corrected trait-method mapping).
        entities=state['bundle']['source_model']['entities']
        edges=state['partition'].get('source_edges')
        if edges is None:
            from .segmentation import dependencies
            edges={n:dependencies(e) for n,e in entities.items()}
        closure=set(source_ids);pending=list(closure)
        while pending:
            for n in edges.get(pending.pop(),[]):
                if n in entities and n not in closure:closure.add(n);pending.append(n)
        context['dependency_context']={
            'sources':{n:entities[n] for n in sorted(closure)},
            'mapping':sorted((r for r in state['mapping'] if r['source'] in closure),key=lambda r:r['source'])}
    if not legacy and schema >= 3:
        # Match the declaration/configuration fallback used by invalidation.
        # Enum variants, aliases and constants can change shared context even
        # when a bounded unit excerpt and ambient imports/impls are unchanged.
        from .translation_workflow import declaration_context
        context['declarations']=declaration_context(state['files'],include_function_signatures=schema>=4)
        context['partition_version']=state['partition']['version']
    from .implementation_strategy import project
    context['strategy']=project(state,closure if not legacy else source_ids,binding=True)
    return fingerprint(context)


def record_review(state,source_ids,review_files,*,check_only=False):
    ledger=state.setdefault('review_work',[])
    if any(r.get('identity_schema')!=4 for r in ledger):
        raise Failure('review_evidence_upgrade_required','Migrate archived review identities against their original snapshots before continuing; do not clear the review ledger')
    identity=review_identity(state,source_ids,review_files)
    row={'identity_schema':4,'unit':state.get('unit'),'identity':identity,'code_characters':sum(map(len,review_files.values())),
         'transaction_count':len(state['transactions'])}
    if any(r['identity']==identity for r in ledger):
        row['repeat']=True
        if not check_only:ledger.append(row)
        # Stop the redundant schedule instead of silently paying for it. Review
        # changes with imports/config/impl bodies have a different identity.
        raise Failure('redundant_review_schedule','An unchanged unit review was scheduled again; inspect invalidation reasons before continuing',row)
    if not check_only:ledger.append(row)
