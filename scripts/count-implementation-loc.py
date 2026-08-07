#!/usr/bin/env python3
"""Count implementation LOC reported in the architecture description."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
RUSTLIGHT_ROOT = REPO_ROOT.parent / "RustLightAST"

STAGE1_ML = [
    REPO_ROOT / "code_rust.ML",
    REPO_ROOT / "code_debug_info.ML",
]
STAGE1_THEORIES = [
    REPO_ROOT / "Rust_Base_Setup.thy",
    REPO_ROOT / "Rust_BigInt_Setup.thy",
    REPO_ROOT / "Rust_BigInt_WordU128_Setup.thy",
    REPO_ROOT / "Rust_Checked128_Setup.thy",
    REPO_ROOT / "Rust_Checked128_WordU128_Setup.thy",
    REPO_ROOT / "Rust_Hybrid128_Setup.thy",
    REPO_ROOT / "Rust_Hybrid128_WordU128_Setup.thy",
    REPO_ROOT / "Rust_Integer_BigInt_Layer.thy",
    REPO_ROOT / "Rust_Integer_Hybrid128_Layer.thy",
]

OPEN_CARTOUCHE = ("\\<open>", "‹")
CLOSE_CARTOUCHE = ("\\<close>", "›")
RAW_STRING_START = re.compile(r"(?:br|cr|r)(?P<hashes>#{0,255})\"")
CHAR_LITERAL = re.compile(
    r"'(?:\\(?:x[0-9A-Fa-f]{2}|u\{[0-9A-Fa-f_]+\}|.)|[^'\\\r\n])'"
)


def matching_token(text: str, offset: int, tokens: tuple[str, ...]) -> str | None:
    return next((token for token in tokens if text.startswith(token, offset)), None)


def blank_except_newlines(text: str) -> str:
    return "".join("\n" if char == "\n" else " " for char in text)


def is_identifier_char(char: str) -> bool:
    return char.isalnum() or char in "_'"


def theory_for_cloc(source: str) -> str:
    """Blank Isabelle comments and documentation, preserving embedded Rust.

    Isabelle theories use ``(* ... *)`` comments but embed Rust in cartouches,
    where expressions such as ``(*value)`` are Rust code.  Treating the entire
    file as Standard ML therefore undercounts the adapters.  This scanner
    removes Isabelle comments and ``text`` commands only outside cartouches;
    the resulting file is counted as Rust so comments in embedded Rust are
    removed by cloc as well.
    """

    output: list[str] = []
    offset = 0
    length = len(source)
    mode = "normal"
    depth = 0
    string_escape = False

    while offset < length:
        if mode == "comment":
            if source.startswith("(*", offset):
                output.append("  ")
                offset += 2
                depth += 1
            elif source.startswith("*)", offset):
                output.append("  ")
                offset += 2
                depth -= 1
                if depth == 0:
                    mode = "normal"
            else:
                output.append("\n" if source[offset] == "\n" else " ")
                offset += 1
            continue

        if mode == "document":
            opener = matching_token(source, offset, OPEN_CARTOUCHE)
            closer = matching_token(source, offset, CLOSE_CARTOUCHE)
            if opener is not None:
                output.append(" " * len(opener))
                offset += len(opener)
                depth += 1
            elif closer is not None:
                output.append(" " * len(closer))
                offset += len(closer)
                depth -= 1
                if depth == 0:
                    mode = "normal"
            else:
                output.append("\n" if source[offset] == "\n" else " ")
                offset += 1
            continue

        if mode == "cartouche":
            opener = matching_token(source, offset, OPEN_CARTOUCHE)
            closer = matching_token(source, offset, CLOSE_CARTOUCHE)
            if opener is not None:
                output.append(opener)
                offset += len(opener)
                depth += 1
            elif closer is not None:
                output.append(closer)
                offset += len(closer)
                depth -= 1
                if depth == 0:
                    mode = "normal"
            else:
                output.append(source[offset])
                offset += 1
            continue

        if mode == "string":
            char = source[offset]
            output.append(char)
            offset += 1
            if string_escape:
                string_escape = False
            elif char == "\\":
                string_escape = True
            elif char == '"':
                mode = "normal"
            continue

        if source.startswith("(*", offset):
            output.append("  ")
            offset += 2
            mode = "comment"
            depth = 1
            continue

        opener = matching_token(source, offset, OPEN_CARTOUCHE)
        if opener is not None:
            output.append(opener)
            offset += len(opener)
            mode = "cartouche"
            depth = 1
            continue

        if source[offset] == '"':
            output.append('"')
            offset += 1
            mode = "string"
            string_escape = False
            continue

        if source.startswith("text", offset):
            before_ok = offset == 0 or not is_identifier_char(source[offset - 1])
            after_text = offset + len("text")
            after_ok = after_text == length or not is_identifier_char(source[after_text])
            cursor = after_text
            while cursor < length and source[cursor].isspace():
                cursor += 1
            doc_opener = matching_token(source, cursor, OPEN_CARTOUCHE)
            if before_ok and after_ok and doc_opener is not None:
                output.append(blank_except_newlines(source[offset:cursor]))
                output.append(" " * len(doc_opener))
                offset = cursor + len(doc_opener)
                mode = "document"
                depth = 1
                continue

        output.append(source[offset])
        offset += 1

    if mode in {"comment", "document", "cartouche", "string"}:
        raise ValueError(f"unterminated {mode} in Isabelle theory")

    return "".join(output)


def rust_code_mask(source: str) -> bytearray:
    """Mark Rust syntax outside comments and string/character literals."""

    mask = bytearray(len(source))
    offset = 0
    length = len(source)

    while offset < length:
        if source.startswith("//", offset):
            newline = source.find("\n", offset + 2)
            offset = length if newline == -1 else newline
            continue

        if source.startswith("/*", offset):
            cursor = offset + 2
            depth = 1
            while cursor < length and depth:
                if source.startswith("/*", cursor):
                    depth += 1
                    cursor += 2
                elif source.startswith("*/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise ValueError("unterminated Rust block comment")
            offset = cursor
            continue

        raw_string = RAW_STRING_START.match(source, offset)
        if raw_string is not None:
            terminator = '"' + raw_string.group("hashes")
            end = source.find(terminator, raw_string.end())
            if end == -1:
                raise ValueError("unterminated Rust raw string")
            offset = end + len(terminator)
            continue

        string_prefix = 2 if source.startswith(('b"', 'c"'), offset) else 0
        if source[offset] == '"' or string_prefix:
            cursor = offset + string_prefix + (0 if string_prefix else 1)
            escaped = False
            while cursor < length:
                char = source[cursor]
                cursor += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    break
            else:
                raise ValueError("unterminated Rust string")
            offset = cursor
            continue

        char_literal = CHAR_LITERAL.match(source, offset)
        if char_literal is not None:
            offset = char_literal.end()
            continue

        mask[offset] = 1
        offset += 1

    return mask


def attribute_end(source: str, mask: bytearray, offset: int) -> int | None:
    cursor = offset + 1
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor == len(source) or source[cursor] != "[" or not mask[cursor]:
        return None

    depth = 0
    while cursor < len(source):
        if mask[cursor]:
            if source[cursor] == "[":
                depth += 1
            elif source[cursor] == "]":
                depth -= 1
                if depth == 0:
                    return cursor + 1
        cursor += 1
    raise ValueError("unterminated Rust attribute")


def rust_item_end(source: str, mask: bytearray, offset: int) -> int:
    paren_depth = 0
    bracket_depth = 0
    cursor = offset

    while cursor < len(source):
        if not mask[cursor]:
            cursor += 1
            continue

        char = source[cursor]
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
        elif char == ";" and paren_depth == 0 and bracket_depth == 0:
            return cursor + 1
        elif char == "{" and paren_depth == 0 and bracket_depth == 0:
            brace_depth = 1
            cursor += 1
            while cursor < len(source) and brace_depth:
                if mask[cursor]:
                    if source[cursor] == "{":
                        brace_depth += 1
                    elif source[cursor] == "}":
                        brace_depth -= 1
                cursor += 1
            if brace_depth:
                raise ValueError("unterminated cfg(test) Rust item")
            return cursor
        cursor += 1

    raise ValueError("cfg(test) attribute is not followed by a complete Rust item")


def without_rust_tests(source: str) -> str:
    """Blank items annotated with ``cfg(test)`` or ``test``."""

    mask = rust_code_mask(source)
    ranges: list[tuple[int, int]] = []
    offset = 0

    while offset < len(source):
        if not mask[offset] or source[offset] != "#":
            offset += 1
            continue

        end = attribute_end(source, mask, offset)
        if end is None:
            offset += 1
            continue

        attribute = source[offset + 1 : end]
        is_cfg_test = re.fullmatch(r"\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]\s*", attribute)
        is_test = re.fullmatch(r"\s*\[\s*test\s*\]\s*", attribute)
        if is_cfg_test is None and is_test is None:
            offset = end
            continue

        end = rust_item_end(source, mask, end)
        ranges.append((offset, end))
        offset = end

    if not ranges:
        return source

    output: list[str] = []
    previous = 0
    for start, end in ranges:
        output.append(source[previous:start])
        output.append(blank_except_newlines(source[start:end]))
        previous = end
    output.append(source[previous:])
    return "".join(output)


def require_sources(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source file(s): " + ", ".join(missing))


def cloc_code(paths: list[Path], force_language: str | None = None) -> int:
    command = ["cloc", "--json", "--quiet"]
    if force_language is not None:
        command.append(f"--force-lang={force_language}")
    command.extend(str(path) for path in paths)
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    return int(report["SUM"]["code"])


def cloc_prepared_rust(paths: list[Path], prepare) -> int:
    with tempfile.TemporaryDirectory(prefix="isabelle2rust-loc-") as temp_dir:
        prepared: list[Path] = []
        for index, source_path in enumerate(paths):
            prepared_path = Path(temp_dir) / f"{index:02d}-{source_path.stem}.rs"
            prepared_path.write_text(
                prepare(source_path.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            prepared.append(prepared_path)
        return cloc_code(prepared)


def count_stage1_theories() -> int:
    return cloc_prepared_rust(
        STAGE1_THEORIES,
        lambda source: without_rust_tests(theory_for_cloc(source)),
    )


def count_rust_implementation(paths: list[Path]) -> int:
    return cloc_prepared_rust(paths, without_rust_tests)


def kloc(lines: int) -> str:
    return f"{lines / 1000:.1f}"


def main() -> int:
    if shutil.which("cloc") is None:
        print("error: make loc requires cloc (https://github.com/AlDanial/cloc)", file=sys.stderr)
        return 2

    try:
        require_sources(STAGE1_ML + STAGE1_THEORIES)
        stage2_sources = sorted((REPO_ROOT / "optimize" / "src").rglob("*.rs"))
        rustlight_sources = sorted((RUSTLIGHT_ROOT / "src").rglob("*.rs"))
        require_sources(stage2_sources)
        require_sources(rustlight_sources)

        stage1 = cloc_code(STAGE1_ML, "Standard ML") + count_stage1_theories()
        stage2 = count_rust_implementation(stage2_sources)
        rustlight = count_rust_implementation(rustlight_sources)
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print("Implementation LOC (blank lines, comments, and test code excluded)")
    print(f"  Stage-1:   {stage1:>6,} LOC ({kloc(stage1)} KLOC)")
    print(f"  Stage-2:   {stage2:>6,} LOC ({kloc(stage2)} KLOC; excludes RustLight)")
    print(f"  RustLight: {rustlight:>6,} LOC ({kloc(rustlight)} KLOC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
