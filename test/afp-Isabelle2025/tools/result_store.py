"""Lazy entry results backed by the run's single transactional database."""
from collections.abc import MutableMapping
import copy
from pathlib import Path

import afp_common as common
from state import State


class EntryStore(MutableMapping):
    def __init__(self, base, scans, scopes):
        self.base = Path(base)
        self.state = State(base)
        self.scans, self.scopes = scans, scopes
        self.cache_key = self.cache_record = None

    def __len__(self):
        return len(self.scans)

    def __iter__(self):
        return iter(self.scans)

    def _pack(self, value):
        if isinstance(value, list):
            return [self._pack(v) for v in value]
        if not isinstance(value, dict):
            return value
        if value.get("log") and "status" in value:
            path = common.resolve_path(value["log"] + ".json")
            original = common.read_record(path)
            if original is not None and path.is_relative_to(self.base.resolve()):
                return {"@command": str(path.relative_to(self.base.resolve())),
                        "fields": {k: v for k, v in value.items() if original.get(k) != v}}
        return {k: self._pack(v) for k, v in value.items()}

    def _unpack(self, value):
        if isinstance(value, list):
            return [self._unpack(v) for v in value]
        if not isinstance(value, dict):
            return value
        if "@command" in value:
            command = self.state.get(value["@command"])
            if command is None:
                raise ValueError("Missing command result: " + value["@command"])
            return dict(command, **value.get("fields", {}))
        return {k: self._unpack(v) for k, v in value.items()}

    def __getitem__(self, key):
        if key not in self.scans:
            raise KeyError(key)
        if key != self.cache_key:
            record = dict(copy.deepcopy(self.scans[key]), **self._unpack(self.state.get("entry/" + key, {})))
            stage = record.get("full_export")
            if stage and stage.get("runs"):
                import full
                for run in stage["runs"]:
                    run["attempts"] = full.collect_attempts(common.resolve_path(run["directory"]))
                # Candidate cells are a view over native XML, never a second
                # persisted catalogue that could disagree with those XML bytes.
                finished = stage.get("finished")
                artifacts = stage.get("artifacts", [])
                full.finish_export(stage, common.candidates(self.scopes[key]))
                stage["finished"] = finished
                stage["artifacts"] = artifacts
            self.cache_key, self.cache_record = key, record
        return self.cache_record

    def __setitem__(self, key, value):
        if key not in self.scans:
            raise KeyError(key)
        self.cache_key, self.cache_record = key, value

    def __delitem__(self, key):
        raise TypeError("The AFP entry set is fixed by the manifest")

    def commit(self, key, compiled=None):
        record = self[key]
        payload = {k: copy.deepcopy(v) for k, v in record.items()
                   if k in {"full_export", "full_compile"}}
        stage = payload.get("full_export", {})
        for name in ("candidates", "languages"):
            if stage.get("runs"):
                stage.pop(name, None)
        for run in stage.get("runs", []):
            run.pop("attempts", None)
        self.state.update({"entry/" + key: self._pack(payload)},
                          remove=["export-progress/" + key + ".json"])
        self.retire(key, record)

    def retire(self, key, record):
        """Remove superseded attempts only after their replacement is committed."""
        keep = {common.resolve_path(r["directory"]) for r in record.get("full_export", {}).get("runs", [])}
        progress = self.state.get("export-progress/" + key + ".json", {})
        for run in [*progress.get("runs", []), *progress.get("retries", []),
                    *([progress["active"]] if progress.get("active") else [])]:
            keep.add(common.resolve_path(run["directory"]))
        for item in record.get("full_compile", {}).values():
            if item.get("directory"):
                keep.add(common.resolve_path(item["directory"]))
            if item.get("stage2"):
                keep.add(common.resolve_path(item["stage2"]))
        for kind in ("exports", "compilation", "rust-stage2"):
            for attempt in (self.base / kind / key).glob("*/attempt-*"):
                if attempt.resolve() not in keep:
                    self.state.remove_tree(attempt)
