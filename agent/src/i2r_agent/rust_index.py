"""Rust syntax locations and conservative references, not name/type resolution."""
import re
from tree_sitter import Language, Parser
import tree_sitter_rust


def build(files):
    parser = Parser(Language(tree_sitter_rust.language()))
    rows, invalid = [], []
    kinds = {'function_item','function_signature_item','struct_item','enum_item','enum_variant','type_item','trait_item','impl_item','const_item','static_item','macro_definition'}
    for path, text in files.items():
        if not path.endswith('.rs'): continue
        data = text.encode(); tree = parser.parse(data)
        if tree.root_node.has_error: invalid.append(path)
        def spelling(node):
            return data[node.start_byte:node.end_byte].decode() if node else ''

        def addressable(node):
            # Local declarations remain diagnostic evidence, but are not crate paths.
            # A non-local impl in a function still adds methods to a global type.
            parent=node.parent
            while parent is not None:
                if parent.type=='impl_item':
                    target=spelling(parent.child_by_field_name('type')).split('<',1)[0].strip()
                    if target.startswith('crate::'):return True
                    head=target.split('::')[0]
                    ancestor=parent.parent
                    while ancestor is not None:
                        if ancestor.type=='mod_item' and not addressable(ancestor):return False
                        if ancestor.type=='block':
                            for declaration in ancestor.named_children:
                                if declaration.type in {'struct_item','enum_item','type_item','mod_item','trait_item'}:
                                    if spelling(declaration.child_by_field_name('name'))==head:return False
                        ancestor=ancestor.parent
                    return True
                if parent.type in {'function_item','block','closure_expression'}:return False
                if parent.type=='mod_item' and not addressable(parent):return False
                parent=parent.parent
            return True

        def lexical_scope(node):
            result=[];parent=node.parent
            while parent is not None:
                if parent.type in {'function_item','block','closure_expression'}:
                    result.append(f'{parent.type}@{parent.start_point.row+1}:{parent.start_point.column+1}')
                parent=parent.parent
            return list(reversed(result))

        def visit(node, scope=(), module_scope=()):
            name = node.child_by_field_name('name')
            label = data[name.start_byte:name.end_byte].decode() if name else None
            if node.type in kinds:
                body = node.child_by_field_name('body')
                attributes=[];previous=node.prev_named_sibling
                while previous is not None and previous.type=='attribute_item':
                    attributes.insert(0,data[previous.start_byte:previous.end_byte].decode());previous=previous.prev_named_sibling
                # macro_export creates a crate-root path regardless of the
                # definition's file/module/block. Plain macro_rules names have
                # lexical scope; without resolving re-exports they are diagnostic-only.
                exported_macro=node.type=='macro_definition' and any(re.fullmatch(
                    r'#\s*\[\s*macro_export\s*(?:\(\s*local_inner_macros\s*\))?\s*\]',a) for a in attributes)
                fragment = data[node.start_byte:node.end_byte].decode()
                refs = set()
                stack = list(node.children)
                while stack:
                    child=stack.pop(); stack.extend(child.children)
                    if child.type in {'identifier','type_identifier'}:
                        refs.add(data[child.start_byte:child.end_byte].decode())
                rows.append({'id':f'{path}:{node.start_point.row+1}', 'file':path,
                    'start_line':node.start_point.row+1,'end_line':node.end_point.row+1,
                    'name':label,'scope':list(scope),'module_scope':list(module_scope),'kind':node.type,
                    'signature':data[node.start_byte:body.start_byte if body else node.end_byte].decode(),
                    'attributes':attributes,'path_addressable':bool(exported_macro) if node.type=='macro_definition' else addressable(node),'lexical_scope':lexical_scope(node),
                    **({'crate_root_path':True} if exported_macro else {}),
                    'references':sorted(refs-({label} if label else set())), 'text':fragment})
            nested=scope;nested_module=module_scope
            if label and node.type in {'mod_item','trait_item','enum_item'}:nested=scope+(label,)
            if label and node.type=='mod_item':nested_module=module_scope+(label,)
            elif node.type=='impl_item':
                target=node.child_by_field_name('type')
                if target:
                    typename=data[target.start_byte:target.end_byte].decode().split('<',1)[0].strip()
                    nested=tuple(typename.split('::')[1:]) if typename.startswith('crate::') else module_scope+tuple(typename.split('::'))
            for child in node.children:
                visit(child,nested,nested_module)
        visit(tree.root_node)
    return {'items':rows,'parse_error_files':invalid,
        'limits':'Syntax references may be ambiguous; compiler diagnostics supply resolved type/borrow evidence. Macro expansions and full alias/type resolution are not analyzed; local items are diagnostic-only.'}


def select(index, feedback, expand=False):
    diagnostic = str(feedback or {})
    roots=[]
    for row in index['items']:
        hits=[int(x) for x in re.findall(re.escape(row['file'])+r':(\d+)',diagnostic)]
        if any(row['start_line']<=n<=row['end_line'] for n in hits) or row.get('name') and re.search(r'\b'+re.escape(row['name'])+r'\b',diagnostic):
            roots.append(row)
    if not roots: return index['items']
    names={r['name'] for r in roots if r['name']}
    references={n for r in roots for n in r['references']}
    rows=[r for r in index['items'] if r in roots or r['name'] in references or names.intersection(r['references'])]
    if expand:
        files={r['file'] for r in rows}
        rows=[r for r in index['items'] if r['file'] in files]
    return rows
