#!/usr/bin/env python3
"""Content-addressed entry results with a bounded in-memory working set.

The small results.json index is the transaction boundary. Entry payloads are
immutable, so interruption between writing a payload and replacing the index
cannot invalidate the previous checkpoint. Full XML evidence remains external.
"""
from collections.abc import MutableMapping
import copy
import hashlib
import json

import afp_common as common


def checksum(value):
    return hashlib.sha256(value).hexdigest()


class EntryStore(MutableMapping):
    def __init__(self, base, summaries, files):
        self.base = base
        self.summaries = summaries
        self.files = files
        self.cache_key = None
        self.cache_record = None

    def __len__(self):
        return len(self.summaries)

    def __iter__(self):
        return iter(self.summaries)

    def __getitem__(self, key):
        if key not in self.summaries:
            raise KeyError(key)
        if self.cache_key != key:
            reference = self.files.get(key)
            if reference:
                path = common.resolve_path(reference["path"])
                raw = path.read_bytes()
                if checksum(raw) != reference["sha256"]:
                    raise ValueError("Entry result bytes changed: " + key)
                record = json.loads(raw)
            else:
                record = copy.deepcopy(self.summaries[key])
            # Only the current entry is cached. Callers must commit mutations
            # before traversing another entry, as the export/compile loops do.
            self.cache_key, self.cache_record = key, record
        return self.cache_record

    def __setitem__(self, key, value):
        if key not in self.summaries:
            self.summaries[key] = {}
        self.cache_key, self.cache_record = key, value

    def __delitem__(self, key):
        raise TypeError("The frozen AFP entry set cannot be reduced")

    def commit(self, key, compiled):
        """Publish immutable payload bytes before updating the small index."""
        record = self[key]
        raw = (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        digest = checksum(raw)
        directory = checksum(key.encode())[:20]
        path = self.base / "entry-results" / directory / (digest + ".json")
        if not path.is_file():
            common.write_json(path, record)
        elif checksum(path.read_bytes()) != digest:
            raise ValueError("Content-addressed result was modified: " + str(path))
        summary = {k: v for k, v in record.items()
                   if not k.startswith("full_export") and not k.startswith("full_compile")}
        stage = record.get("full_export", {})
        summary["full_export"] = {k: v for k, v in stage.items()
                                  if k not in ("runs", "candidates", "artifacts")}
        summary["_compiled_candidates"] = {p: sorted(cs) for p, cs in compiled.items()}
        self.summaries[key] = summary
        self.files[key] = {
            "path": common.relative(path), "sha256": digest,
            "export_sha256": checksum(json.dumps(stage, sort_keys=True).encode())}

    def serialize(self, result):
        return dict(result, entries=self.summaries, entry_files=self.files,
                    result_storage="content-addressed-entries-v1")
