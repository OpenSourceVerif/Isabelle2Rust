#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_VERSION = 2
ROOT = Path(__file__).resolve().parent
CACHE_PATH = ROOT / ".ocaml-glue-cache.json"
BACKUP_ROOT = ROOT / "backups" / "ocaml-glue"


@dataclass(frozen=True)
class InjectionJob:
    name: str
    source: Path
    target: Path
    module_lower: str
    module_upper: str
    end_marker: str
    glue_marker: str
    use_target_signature: bool


JOBS = [
    InjectionJob(
        name="x64_encode",
        source=ROOT.parent / "theory/stage1/x64EncodeGenerator/x64_encode.ocaml",
        target=ROOT / "2-exec-assembler/x64_encode.ml",
        module_lower="x64_encode",
        module_upper="X64_encode",
        end_marker="end;; (*struct x64_encode*)",
        glue_marker="let i64_MIN",
        use_target_signature=False,
    ),
    InjectionJob(
        name="x64_step_test",
        source=ROOT.parent / "theory/stage1/x64StepGenerator/x64_step_test.ocaml",
        target=ROOT / "5-exec-semantics/x64_step_test.ml",
        module_lower="x64_step_test",
        module_upper="X64_step_test",
        end_marker="end;; (*struct x64_step_test*)",
        glue_marker="let i64_MIN",
        use_target_signature=True,
    ),
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT.parent.parent))
    except ValueError:
        return str(path)


def load_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text())


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def normalize_generated(text: str, job: InjectionJob) -> str:
    text = re.sub(rf"\bmodule\s+{re.escape(job.module_lower)}\b", f"module {job.module_upper}", text, count=1)
    # Isabelle's OCaml backend emits a local type named "int"; the existing glue
    # expects "myint" to avoid colliding with OCaml's builtin int type.
    text = re.sub(r"\bint\b", "myint", text)
    return text


def before_marker(text: str, marker: str, path: Path) -> str:
    idx = text.rfind(marker)
    if idx < 0:
        raise RuntimeError(f"cannot find marker {marker!r} in {path}")
    return text[:idx]


def after_marker(text: str, marker: str, path: Path) -> str:
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError(f"cannot find marker {marker!r} in {path}")
    return text[idx:]


def struct_body(text: str, path: Path) -> str:
    marker = "= struct"
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError(f"cannot find {marker!r} in {path}")
    return text[idx + len(marker):]


def target_signature_prefix(text: str, path: Path) -> str:
    marker = "= struct"
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError(f"cannot find {marker!r} in {path}")
    return text[:idx + len(marker)]


def compose(job: InjectionJob) -> tuple[str, str]:
    generated_raw = job.source.read_text()
    target_text = job.target.read_text()
    generated = normalize_generated(generated_raw, job)
    glue = after_marker(target_text, job.glue_marker, job.target)

    if job.use_target_signature:
        prefix = target_signature_prefix(target_text, job.target)
        body = before_marker(struct_body(generated, job.source), job.end_marker, job.source)
        body = before_marker(body, "let rec x64_step_test", job.source)
        output = prefix + body.rstrip() + "\n\n" + glue.lstrip()
    else:
        body = before_marker(generated, job.end_marker, job.source)
        output = body.rstrip() + "\n\n" + glue.lstrip()

    return output, generated_raw


def backup_target(job: InjectionJob, backup_dir: Path) -> Path:
    rel = job.target.relative_to(ROOT)
    backup_path = backup_dir / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(job.target, backup_path)
    return backup_path


def run(force: bool) -> int:
    cache = load_cache()
    backup_dir: Path | None = None
    changed = 0

    for job in JOBS:
        if not job.source.exists():
            raise FileNotFoundError(job.source)
        if not job.target.exists():
            raise FileNotFoundError(job.target)

        source_hash = sha256_file(job.source)
        target_hash = sha256_file(job.target)
        entry = cache.get(job.name, {})

        if (
            not force
            and entry.get("script_version") == SCRIPT_VERSION
            and entry.get("source_hash") == source_hash
            and entry.get("target_hash") == target_hash
        ):
            print(f"[skip] {job.name}: source and target match cache")
            continue

        output, generated_raw = compose(job)
        output_hash = sha256_text(output)

        if output_hash == target_hash:
            print(f"[ok]   {job.name}: already up to date")
        else:
            if backup_dir is None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir = BACKUP_ROOT / stamp
            backup_path = backup_target(job, backup_dir)
            job.target.write_text(output)
            changed += 1
            print(f"[write] {job.name}: updated {job.target.relative_to(ROOT)}")
            print(f"        backup: {backup_path.relative_to(ROOT)}")

        cache[job.name] = {
            "script_version": SCRIPT_VERSION,
            "source": display_path(job.source),
            "target": display_path(job.target),
            "source_hash": source_hash,
            "generated_raw_hash": sha256_text(generated_raw),
            "target_hash": output_hash,
        }

    save_cache(cache)
    print(f"done: {changed} file(s) updated")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject x64 OCaml validation glue into freshly exported Isabelle code.")
    parser.add_argument("--force", action="store_true", help="rebuild target files even when the cache matches")
    args = parser.parse_args()
    return run(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
