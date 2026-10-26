#!/usr/bin/env python3
"""Retain discovery receipts for an explicitly selected candidate boundary."""
import hashlib
import shutil

import afp_common as common


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_receipts(base, source, result, files):
    """Copy committed receipts; an interrupted uncommitted attempt is excluded."""
    index = {}
    for record in result["entries"].values():
        scan = record["scan"]
        for session, unit in scan.get("unit_ids", {}).items():
            if unit in index:
                continue
            pointer = common.read_json(source / "units" / unit / "current.json")
            original = source / pointer["receipt"]
            if checksum(original) != pointer["sha256"]:
                raise ValueError("Discovery receipt changed: " + session)
            receipt = common.read_json(original)
            if receipt["status"] != scan["unit_states"][session]:
                raise ValueError("Receipt does not match selected snapshot: " + session)
            name = "receipts/" + unit + ".json"
            saved = base / "baseline" / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, saved)
            files[name] = checksum(saved)
            index[unit] = {"session": session, "original": common.relative(original),
                           "receipt": common.relative(saved), "sha256": files[name],
                           "status": receipt["status"],
                           "dependencies": receipt.get("dependencies", [])}
    common.write_json(base / "baseline/receipt-index.json", index)
    files["receipt-index.json"] = checksum(base / "baseline/receipt-index.json")
    return index


def receipts(base, scan):
    """Use retained receipt paths, never a later mutable scanner head."""
    index = common.read_json(base / "baseline/receipt-index.json", {})
    for unit in scan.get("unit_ids", {}).values():
        item = index.get(unit)
        if item:
            path = common.PROJECT / item["receipt"]
            yield path, common.read_json(path)


def dependencies(base, scan):
    """Name root prerequisites explicitly instead of reporting an empty reason."""
    inherited = scan.get("session_dependencies", scan.get("dependencies", []))
    return sorted(set(inherited) | {
        dependency for _, receipt in receipts(base, scan)
        for dependency in receipt.get("dependencies", [])})


def messages(base, scan):
    """Find complete failed-session messages pinned by selected unit receipts.

    Per-unit archives belong to the failed command interval. Never consult a
    newer scanner pointer or the mutable global Isabelle session database.
    """
    failed = {session for phase in ("loading", "inspections") for check in scan.get(phase, [])
              for session in check.get("failed_sessions", [])}
    boundary = common.read_json(base / "candidate-baseline.json", {})
    if not failed or not boundary.get("source"):
        return {}
    source = common.PROJECT / boundary["source"]
    result = {}
    for receipt_path, receipt in receipts(base, scan):
        for name, expected in receipt.get("evidence", {}).items():
            if not name.endswith("/scan-messages/index.json"):
                continue
            path = source / name
            if not path.is_file():
                continue
            # Keep verification metadata explicit so both the independent audit
            # and report can reject an index changed after receipt commitment.
            verified = checksum(path) == expected["sha256"]
            for session, value in common.read_json(path, {}).items():
                if session in failed:
                    result[session] = dict(value, receipt_index=common.relative(path),
                        receipt_index_sha256=expected["sha256"], receipt_index_verified=verified,
                        receipt=common.relative(receipt_path))
    return result
