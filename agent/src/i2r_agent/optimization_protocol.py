"""Performance-stage protocol and callable interface checks.

Envelope normalization never changes a source string or invents an action.
The original correctness-generation response and cache protocols are untouched.
"""
from copy import deepcopy
import json
import re
from .common import Failure
from .response_protocol import normalize as translation_normalize
from .verification_identity import interfaces_for_cache


ACTIONS = {'rust', 'source', 'inspect', 'finish'}
EXAMPLES = '''Use an explicit top-level action discriminator, for example:
{"action":"rust","files":{"src/lib.rs":"complete file text"},"strategy_version":"exact supplied version","strategy_updates":[...],"reason":"...","evidence":"..."}
{"action":"source","definitions":"HOL declarations and proved lemmas","replacements":[{"source":"original source ID","rhs":"HOL term","proof":"by ..."}],"reason":"..."}
{"action":"inspect","request_sources":[{"path":"exact source_material_catalog path","start_line":1,"end_line":100}],"reason":"Read existing definitions and proof lemmas before choosing or repairing a source transformation"}
{"action":"finish","reason":"...","source_assessment":"required in full mode"}
All fields belong to this one object; do not nest them under the action name. Existing A0 public traits (including restricted pub visibility) cannot gain overridable methods or associated members, even default or doc(hidden) ones; use private free helpers. Private free helpers may change signature or be renamed/removed together with their callers and mappings; frozen tests and connectors must still compile unchanged. Existing method bodies may still be optimized under the shared scope gate.'''


def normalize(reply):
    if not isinstance(reply, dict):
        raise Failure('invalid_optimization_action', EXAMPLES)
    result = deepcopy(reply)
    tags = ACTIONS & result.keys()
    if tags:
        if len(tags) != 1:
            raise Failure('invalid_optimization_action', 'Multiple tagged actions; ' + EXAMPLES)
        tag = next(iter(tags)); body = result.pop(tag)
        if not isinstance(body, dict) or result.get('action', tag) != tag:
            raise Failure('invalid_optimization_action', 'Conflicting or malformed tagged action; ' + EXAMPLES)
        for key, value in body.items():
            if key in result and result[key] != value:
                raise Failure('invalid_optimization_action', 'Conflicting envelope field: ' + key)
            result[key] = value
        if result.get('action', tag) != tag:
            raise Failure('invalid_optimization_action', 'Conflicting nested action')
        result['action'] = tag
    if result.get('action') not in ACTIONS:
        raise Failure('invalid_optimization_action', EXAMPLES,
                      {'received_action': result.get('action'), 'received_keys': sorted(result)})
    result, _ = translation_normalize(result)
    # Assessment is explanatory evidence, not executable code. Preserve a
    # structured assessment losslessly in the controller's textual log format.
    def has_text(value):
        if isinstance(value, str): return bool(value.strip())
        if isinstance(value, dict): return any(has_text(v) for v in value.values())
        if isinstance(value, list): return any(has_text(v) for v in value)
        return False
    assessment = result.get('source_assessment')
    if isinstance(assessment, (dict, list)) and has_text(assessment):
        result['source_assessment'] = json.dumps(assessment, ensure_ascii=False, sort_keys=True)
    return result


def signature_tokens(signature):
    """Retain Rust syntax except local parameter patterns and trivia.

Types, bounds, receivers, ABI, visibility and qualifiers remain authoritative.
The frozen compiler/test/observer checks subsequently resolve actual bindings.
"""
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    parser = Parser(Language(tree_sitter_rust.language()))
    data = (signature.rstrip().removesuffix(';') + ' {}').encode()
    tree = parser.parse(data)
    if tree.root_node.has_error:
        raise Failure('optimization_interface_parse_error', signature)
    result = []
    def visit(node):
        if node.type in {'line_comment', 'block_comment', 'block'}:
            return
        if node.type == 'parameter':
            result.append(('parameter',))
            for child in node.named_children:
                if child.type == 'attribute_item': visit(child)
            visit(node.child_by_field_name('type'))
        elif not node.children:
            result.append((node.type, data[node.start_byte:node.end_byte].decode()))
        else:
            for child in node.children: visit(child)
    visit(tree.root_node)
    return result


def interfaces(files):
    """Freeze callable APIs, not the signatures of private free helpers.

    A changed helper still goes through mapping, compilation and the unchanged
    source/connector tests. Trait and impl members retain their existing checks;
    they are not classified as free functions by the Rust index.
    """
    result = interfaces_for_cache(files)
    for name, rows in list(result.items()):
        retained = []
        for row in rows:
            if row['kind'] in {'function_item', 'function_signature_item'}:
                row['signature'] = signature_tokens(row['signature'])
                exported_symbol = any(re.search(r'\b(?:no_mangle|export_name)\b', attr)
                                      for attr in row.get('attributes', []))
                if (row['kind'] == 'function_item' and row.get('scope') == row.get('module_scope')
                        and not exported_symbol and not any(token[0] == 'pub' for token in row['signature'])):
                    continue
            retained.append(row)
        if retained:
            result[name] = retained
        else:
            del result[name]
    return result


def public_trait_members(files, only=None):
    """Inventory direct members of existing visible, addressable traits.

    Reuse the same qualified item paths as frozen interface checks. This is a
    performance-only syntactic boundary, not Rust macro/type/visibility analysis.
    Restricted pub visibility is included conservatively; new/private traits
    are outside the member freeze. Unresolved frozen trait bodies fail closed.
    """
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    from .rust_index import build
    from .segmented_contract import items
    indexed = build(files)
    if indexed['parse_error_files']:
        raise Failure('optimization_trait_contract_parse_error', 'Cannot verify the frozen trait contract in malformed Rust',
                      indexed['parse_error_files'])
    parser = Parser(Language(tree_sitter_rust.language())); result = {}
    kinds = {'function_item': 'method', 'function_signature_item': 'method',
             'associated_type': 'type', 'type_item': 'type', 'const_item': 'const'}
    trivia = {'attribute_item', 'inner_attribute_item', 'line_comment', 'block_comment', 'empty_statement'}
    for path, rows in items(files).items():
        if only is not None and path not in only:
            continue
        traits = [row for row in rows if row['kind'] == 'trait_item']
        if not traits:
            continue
        visible = []
        for row in traits:
            tree = parser.parse(row['text'].encode())
            nodes = [n for n in tree.root_node.named_children if n.type == 'trait_item']
            if tree.root_node.has_error or len(nodes) != 1:
                raise Failure('optimization_trait_contract_parse_error', 'Cannot parse trait declaration', path)
            if any(n.type == 'visibility_modifier' for n in nodes[0].named_children):
                visible.append(nodes[0])
        if not visible:
            continue
        if len(visible) != 1:
            raise Failure('optimization_trait_contract_ambiguous', 'Frozen public trait identity must be unique', path)
        trait = visible[0]
        members = set()
        body = trait.child_by_field_name('body')
        if body is None:
            raise Failure('optimization_trait_contract_parse_error', 'Missing frozen trait body', path)
        for child in body.named_children:
            if child.type in trivia:
                continue
            name = child.child_by_field_name('name')
            if child.type not in kinds or name is None:
                raise Failure('optimization_trait_contract_unresolved',
                              'Frozen public trait members must be explicit; macro-expanded or unknown members cannot be verified',
                              {'trait': path, 'kind': child.type})
            member = (kinds[child.type], name.text.decode())
            if member in members:
                raise Failure('optimization_trait_contract_ambiguous', 'Duplicate frozen trait member',
                              {'trait': path, 'member': member})
            members.add(member)
        result[path] = members
    return result


def ensure_public_trait_members(original_files, candidate_files):
    """No new override points on A0 public traits, even with default bodies."""
    before = public_trait_members(original_files)
    after = public_trait_members(candidate_files, only=set(before))
    missing = sorted(set(before) - set(after))
    added = {name: sorted(after[name] - members) for name, members in before.items()
             if name in after and after[name] - members}
    removed = {name: sorted(members - after[name]) for name, members in before.items()
               if name in after and members - after[name]}
    if missing or added or removed:
        raise Failure('optimization_trait_contract_changed',
                      'Keep every A0 public trait member set fixed. New overridable methods or associated members add generic obligations even with default implementations or doc(hidden); use private free helpers.',
                      {'missing_traits': missing, 'added_members': added, 'removed_members': removed})
