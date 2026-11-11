"""Request-bound edits and trial-local execution evidence, shared by both crates."""
from copy import deepcopy
import difflib
from pathlib import Path

from .common import Failure, read, save
from .task_context import Archive, fingerprint


class EditController:
    # Only rejected/no-op actions on unchanged files count. Compilation and
    # behavioral failures after real edits never trigger this protocol limit.
    RECOVERY_AFTER = 2
    STOP_AFTER = 4

    def __init__(self, directory, scope, archive=None):
        self.directory = Path(directory)
        self.scope = scope
        self.archive = archive or Archive(self.directory / 'materials')
        self.path = self.directory / 'actions.json'
        self.events = read(self.path) if self.path.exists() else []

    def file_id(self, name):
        return 'connector/' + name if self.scope == 'connector' else name

    def protocol(self, files):
        return {'scope': self.scope, 'snapshot_version': self.archive.put('code', files),
                'version_binding': 'The controller binds this response to this request snapshot. '
                    'base_code_version is optional; an explicitly supplied stale version is rejected.',
                'editable_files': [self.file_id(n) for n in sorted(files)],
                'paths': 'Read and edit the same file ID. Crate-relative src/... aliases are also accepted. '
                    'Other crates are read-only. New Rust files use the same namespace.',
                'edits': 'Use edits:[{file,old,new}] with unique exact old text; '
                    'files:{file:complete_content} replaces whole files atomically.'}

    def context(self, files):
        version = 'code-' + fingerprint(files)
        pending = []
        for event in reversed(self.events):
            if event['before_version'] != version or event['applied']:
                break
            if event.get('error'):
                pending.append(event)
            else:
                break
        pending.reverse()
        failures = []
        for event in pending:
            error = event.get('error')
            if error and error not in failures:
                failures.append(error)
        recovery = len(pending) >= self.RECOVERY_AFTER
        return {'scope': self.scope, 'current_version': version,
                'consecutive_unapplied_actions': len(pending),
                'unresolved_action_errors': failures,
                # Full patches/diffs are archived; the last two are included
                # exactly, not replaced by the model's self-reported diagnosis.
                'recent_actions': self.events[-4:],
                'recent_patch_proposals': [self.archive.get(e['proposal_version']) for e in pending[-2:]],
                'recovery': 'replace_files' if recovery else None,
                'next_step': ('No code has changed. All errors above remain action constraints. '
                    'Use the supplied complete current files and return a complete replacement of the affected file; '
                    'do not repeat rejected text edits. Original program failure still requires validation.'
                    if recovery else 'Applied edits still require compilation and behavioral validation.'),
                'protocol_failure_limit': self.STOP_AFTER}

    def apply(self, current, reply, snapshot, directory, require_change=False, metadata_before=None, metadata_after=None):
        """Apply only to the snapshot sent with THIS call; never mutate caller data."""
        from .knowledge import apply_files
        directory = Path(directory)
        normalizations = []
        try:
            version = 'code-' + fingerprint(snapshot)
            if current != snapshot:
                raise Failure('stale_patch', 'Files changed after this request; reread before editing',
                              {'request_version': version, 'current_version': 'code-' + fingerprint(current)})
            if reply.get('base_code_version') is not None and reply['base_code_version'] not in {version, version[5:]}:
                raise Failure('stale_patch', 'Explicit patch version does not match this request snapshot',
                              {'request_version': version, 'supplied_version': reply['base_code_version']})
            effective = deepcopy(reply)
            effective['base_code_version'] = version

            def local(name):
                if not isinstance(name, str):raise Failure('invalid_edit', 'File ID must be a string')
                prefix = self.scope + '/'
                if name.startswith(prefix):
                    stripped = name[len(prefix):]
                    normalizations.append({'file': name, 'local_path': stripped})
                    return stripped
                if name.startswith(('algorithm/', 'connector/')):
                    raise Failure('read_only_edit', 'This crate is read-only in the current operation',
                                  {'file': name, 'editable_files': self.protocol(current)['editable_files']})
                return name

            incoming = effective.get('files', {})
            if not isinstance(incoming, dict):raise Failure('invalid_candidate', 'files must be an object')
            normalized = {}
            for name, content in incoming.items():
                key = local(name)
                if key in normalized:raise Failure('invalid_edit', 'Two file IDs refer to the same replacement target', key)
                normalized[key] = content
            effective['files'] = normalized
            edits = effective.get('edits', [])
            if not isinstance(edits, list):raise Failure('invalid_edit', 'edits must be an array')
            for edit in edits:
                if not isinstance(edit, dict) or 'file' not in edit:
                    raise Failure('invalid_edit', 'Each edit needs file, old and new')
                edit['file'] = local(edit['file'])
            result = apply_files(current, effective, directory / 'file-normalizations.json')
            if 'src/lib.rs' not in result:
                raise Failure('invalid_candidate', 'Return the crate root src/lib.rs')
            if require_change and result == current:
                raise Failure('unchanged_repair', 'No code was changed; inspect the current files and action errors')
        except Failure as error:
            self.reject(current, reply, error, directory, snapshot)
            raise
        self.record(current, result, reply, directory, snapshot, normalizations=normalizations,
                    metadata_before=metadata_before,metadata_after=metadata_after)
        return result

    def reject(self, current, reply, error, directory, snapshot=None):
        # Caller can also record schema/read errors raised before apply().
        event_path = Path(directory) / 'edit-operation.json'
        if not event_path.exists():
            self.record(current, current, reply or {}, directory, snapshot if snapshot is not None else current,
                        error={'status': error.code, 'message': str(error), 'evidence': error.evidence})
        state = self.context(current)
        if self.STOP_AFTER is not None and state['consecutive_unapplied_actions'] >= self.STOP_AFTER:
            raise Failure('repair_protocol_stalled',
                          'Repeated actions could not modify the current files, including after full-file recovery. '
                          'The original defect remains unresolved.', state)

    def record(self, before, after, reply, directory, snapshot, error=None, normalizations=None, metadata_before=None, metadata_after=None):
        directory = Path(directory)
        changed = [n for n in sorted(set(before) | set(after)) if before.get(n) != after.get(n)]
        diff = ''.join(''.join(difflib.unified_diff(before.get(n, '').splitlines(True), after.get(n, '').splitlines(True),
                        fromfile=self.file_id(n) + ' (before)', tofile=self.file_id(n) + ' (after)')) for n in changed)
        metadata_changed=metadata_before!=metadata_after
        applied=bool(changed) or metadata_changed
        event = {'scope': self.scope, 'request_version': self.archive.put('code', snapshot),
                 'before_version': self.archive.put('code', before), 'after_version': self.archive.put('code', after),
                 'applied': applied, 'code_changed':bool(changed),'metadata_changed':metadata_changed,
                 'outcome': 'rejected' if error else 'applied' if applied else 'unchanged',
                 'changed_files': [self.file_id(n) for n in changed], 'error': error,
                 'proposal_version': self.archive.put('event', {'reply': deepcopy(reply)}),
                 'diff_version': self.archive.put('event', {'diff': diff}),
                 'path_normalizations': normalizations or [], 'validation': 'not_run',
                 'evidence_path': str(directory / 'edit-operation.json')}
        if metadata_before is not None:
            event['metadata_before']=self.archive.put('event',metadata_before)
            event['metadata_after']=self.archive.put('event',metadata_after)
        save(directory / 'edit-operation.json', event)
        (directory / 'edit-changes.diff').write_text(diff)
        self.events.append(event)
        save(self.path, self.events)

    def verify(self, files, kind, status, evidence_path):
        """Attach executed checks, never infer success from an accepted patch."""
        version = 'code-' + fingerprint(files)
        for event in reversed(self.events):
            if event['applied'] and event['after_version'] == version:
                event.setdefault('checks', []).append({'kind': kind, 'status': status, 'evidence_path': str(evidence_path)})
                event['validation'] = 'checks_recorded'
                save(self.path, self.events)
                break
