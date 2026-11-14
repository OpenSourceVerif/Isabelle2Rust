"""Encode performance proposals with the configured Isabelle symbol registry.

This is notation transport, not proof repair. The original proposal is retained,
and the same encoded fragments go to both the trusted lexer and the prover.
"""
from copy import deepcopy
from pathlib import Path
import re
from .common import Failure, digest, save
from .task_context import fingerprint


def encoding(specifications):
    declarations = {}
    for text in specifications:
        for line in text.splitlines():
            match = re.match(r'\s*(\\<[^>]+>)\s+.*?\bcode:\s*(0x[0-9a-fA-F]+)\b', line)
            if match:
                declarations[match[1]] = int(match[2], 16)
    return {chr(code): symbol for symbol, code in declarations.items() if code >= 128}


def encode_proposal(proposal, symbols):
    result = deepcopy(proposal); changes = []
    def recode(text, location):
        if not isinstance(text, str): return text  # The existing renderer owns shape errors.
        encoded = ''.join(symbols.get(c, c) for c in text)
        if encoded != text:
            changes.append({'field': location, 'before': fingerprint(text), 'after': fingerprint(encoded),
                            'symbols': {c: symbols[c] for c in sorted(set(text)) if c in symbols}})
        return encoded
    result['definitions'] = recode(result.get('definitions'), 'definitions')
    for i, row in enumerate(result.get('replacements', [])):
        for field in ('rhs', 'proof'):
            row[field] = recode(row.get(field), f'replacements[{i}].{field}')
    return result, changes


def prepare(proposal, cfg, executor, directory):
    fragments = [proposal.get('definitions', '')] + [r.get(k, '') for r in proposal.get('replacements', []) for k in ('rhs', 'proof')]
    if not any(isinstance(t, str) and any(ord(c) >= 128 for c in t) for t in fragments):
        return proposal, None
    result = executor.run([cfg['tools']['isabelle'], 'getenv', '-b', 'ISABELLE_SYMBOLS'], timeout=30)
    paths = Path(result['stdout']).read_text().strip().split(':')
    specs = []; records = []
    for name in paths:
        optional = name.endswith('?'); path = Path(name[:-1] if optional else name)
        if not path.is_file():
            if optional: continue
            raise Failure('isabelle_symbol_registry_missing', str(path))
        specs.append(path.read_text()); records.append({'path': str(path), 'sha256': digest(path)})
    if not specs: raise Failure('isabelle_symbol_registry_missing', 'Configured Isabelle returned no symbol tables')
    effective, changes = encode_proposal(proposal, encoding(specs))
    evidence = {'policy': 'configured-isabelle-symbol-encoding-v1', 'registries': records,
                'original_proposal': fingerprint(proposal), 'effective_proposal': fingerprint(effective),
                'changes': changes, 'proof_repair': False}
    save(Path(directory)/'source-text-encoding.json', evidence)
    save(Path(directory)/'effective-proposal.json', effective)
    return effective, evidence
