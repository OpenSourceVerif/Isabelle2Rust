"""Resolve current scan evidence directly from the run database."""
import afp_common as common
from state import State


def receipts(base, scan):
    state = State(base)
    for unit in scan.get("unit_ids", {}).values():
        receipt = state.get("receipt/" + unit)
        if receipt:
            yield state.base / "state.sqlite3", receipt


def dependencies(base, scan):
    return sorted({d for _, receipt in receipts(base, scan) for d in receipt.get("dependencies", [])})


def read_messages(base):
    index = common.read_record(base / "scan-messages/index.json", {})
    for item in index.values():
        if isinstance(item.get("command"), str):
            item["command"] = common.read_record(common.resolve_path(item["command"]), {})
    return index


def messages(base, scan):
    result = {}
    for _, receipt in receipts(base, scan):
        directory = receipt.get("directory")
        if directory:
            for session, item in read_messages(base / directory).items():
                from scan_store import file_digest
                log = common.resolve_path(item.get("command", {}).get("log", "__missing__"))
                verified = log.is_file() and file_digest(log) == item.get("messages_sha256")
                result[session] = dict(item, receipt_index_verified=verified)
    return result
