"""Pinned, additive Isabelle2025 Code_Target observation interface.

No replacement ML structure is loaded into an existing theory/heap. The only
source change exposes the exact printing data already used by serializers.
"""
import hashlib
from pathlib import Path
import stat

ORIGINAL_SHA256 = "902bfdf8dd6eb109d4a98d2adbea518fbf8ba8f28130ba2d421ae7da416c469b"
RELATIVE = "src/Tools/Code/code_target.ML"
DECL = "  val get_printings: Proof.context -> string -> Code_Printer.printings\n"
IMPL = """(* Read-only AFP analysis interface: use the native inheritance merge. *)
fun get_printings ctxt target_name =
  (Code_Printer.the_printings o snd o snd)
    (join_ancestry (Proof_Context.theory_of ctxt) target_name);

"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def original(data):
    return data.replace(DECL.encode(), b"").replace(IMPL.encode(), b"")


def patched(data):
    if sha(original(data)) != ORIGINAL_SHA256:
        raise ValueError("Code_Target source is not the pinned Isabelle2025 revision")
    source = original(data).decode()
    source = source.replace("  val set_identifiers:", DECL + "  val set_identifiers:", 1)
    return source.replace("fun allocate_target ", IMPL + "fun allocate_target ", 1).encode()


def verify(home):
    path = Path(home) / RELATIVE
    data = path.read_bytes()
    if data != patched(data):
        raise ValueError("Install the pinned read-only Code_Target patch and rebuild heaps: "
                         "python3 setup/patch_isabelle.py")
    return {"interface": "code-target-get-printings-v1", "source": RELATIVE,
            "original_sha256": ORIGINAL_SHA256, "sha256": sha(data)}


def apply(home):
    path = Path(home) / RELATIVE
    data = path.read_bytes()
    wanted = patched(data)
    if data != wanted:
        # Isabelle release archives mark source trees read-only. Temporarily
        # grant only the owner write access, then restore the exact mode.
        mode = stat.S_IMODE(path.stat().st_mode)
        try:
            if not (mode & stat.S_IWUSR):
                path.chmod(mode | stat.S_IWUSR)
            path.write_bytes(wanted)
        finally:
            path.chmod(mode)
    return verify(home)
