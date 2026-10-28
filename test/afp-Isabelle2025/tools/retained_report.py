#!/usr/bin/env python3
"""Audit retained case evidence and links, without claiming a full export audit."""
import json
from pathlib import Path
import re

from scan_store import file_digest


def verify(experiment):
    experiment = Path(experiment).resolve()
    report = experiment / 'report'
    selected = [json.loads(s) for s in (report / 'selected-evidence.jsonl').read_text().splitlines()]
    for row in selected:
        p = experiment / row['path']
        if (not p.resolve().is_relative_to(experiment) or not p.is_file()
                or p.stat().st_size != row['bytes'] or file_digest(p) != row['sha256']):
            raise ValueError('Selected evidence changed: ' + row['path'])
    links = 0
    for p in report.glob('*.md'):
        for raw in re.findall(r'\]\(<?([^)>]+)>?\)', p.read_text()):
            if '://' in raw or raw.startswith('#'):
                continue
            target = (p.parent / raw.split('#', 1)[0]).resolve()
            if not target.is_file():
                raise ValueError('Broken report link: ' + p.name + ': ' + raw)
            links += 1
    # Large historical tables retain their original bytes and statistics.
    # Narrative files only receive relocation links and retention notices.
    original = json.loads((experiment / 'setup/report-original-files.json').read_text())
    for name, row in original.items():
        if not name.endswith('.md') and file_digest(report / name) != row['sha256']:
            raise ValueError('Historical report table/index changed: ' + name)
    return {'passed': True, 'selected_files': len(selected), 'narrative_links': links,
            'full_export_evidence_available': False, 'full_export_reaudit_performed': False}
