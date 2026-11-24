#!/usr/bin/env python3
"""Integration regressions for loaded-theory provenance and independent branches."""

import sys
import xml.etree.ElementTree as ET

from afp_common import (HERE, arguments, build_lock, build_options, command, environment)
import scan


def main():
    args = arguments(__doc__).parse_args()
    env, _ = environment(args)
    work = HERE.parent / "work/_tmp/scanner-fixture"
    work.mkdir(parents=True, exist_ok=True)
    fixtures = HERE.parent / "tests/fixtures"
    logs = HERE.parent / "work/logs/scanner-fixture"
    baseline = {"Origin": ["Origin.late_equation"], "Later": ["Later.ordinary"],
                "Other": ["Other.independent"]}
    # The second case preserves later equations in compatible branches while
    # adding incompatible definitions of a shared constant. Its declarations
    # must remain discoverable even though a synthetic global import cannot load.
    branches = dict(baseline, Branch_Base=[],
                    Branch_Left=["Branch_Left.branch_value_bool_inst.branch_choice_bool",
                                 "Branch_Left.left_marker"],
                    Branch_Right=["Branch_Right.branch_value_bool_inst.branch_choice_bool",
                                  "Branch_Right.right_marker"])
    with build_lock():
        loaded = command([args.isabelle, "build", "-b", *build_options(args),
                          "-d", str(fixtures), "AFP-Scan-Fixture"],
                         logs / "load.log", args, env)
        if loaded["status"] != "passed":
            raise RuntimeError("Fixture load failed: " + loaded["log"])
        for case, expected in (("baseline", baseline), ("branches", branches)):
            names = work / (case + ".theories")
            output = work / (case + ".xml")
            expected = {"AFP-Scan-Fixture." + name: values
                        for name, values in expected.items()}
            names.write_text("\n".join(expected) + "\n")
            output.unlink(missing_ok=True)
            # Use the production entry so the code preprocessor ML namespace
            # and certificate simpset match real AFP scans, including branches.
            inspected = scan.inspect_session(
                "AFP-Scan-Fixture", args,
                dict(env, AFP_SCAN_THEORIES=str(names), AFP_SCAN_OUTPUT=str(output)),
                logs / (case + ".scan.log"), directories=[fixtures])
            if inspected["status"] != "passed":
                raise RuntimeError("Fixture inspection failed: " + inspected["log"])
            document = ET.parse(output).getroot()
            if document.attrib.get("certificate_context") != scan.CERTIFICATE_CONTEXT:
                raise AssertionError("Unexpected certificate preprocessing context")
            actual = {}
            for theory in document.findall("theory"):
                actual.setdefault(theory.attrib["name"], set()).update(
                    c.attrib["name"] for c in theory.findall("constant"))
            actual = {name: sorted(values) for name, values in actual.items()}
            if actual != expected or list(document.iter("error")):
                raise AssertionError("Loaded-theory scope mismatch: " + repr(actual))
            # A branch fallback is a reported discovery context, not an export
            # success: the aggregate export still exposes conflicting imports.
            if bool(document.findall("context_merge_error")) != (case == "branches"):
                raise AssertionError("Unexpected context merge diagnostics: " + case)
            print("Scanner integration passed: " + case, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
