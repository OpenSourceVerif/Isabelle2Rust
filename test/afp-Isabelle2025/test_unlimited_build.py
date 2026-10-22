#!/usr/bin/env python3
"""Opt-in Isabelle integration regression for ROOT-local build timeouts.

Run with AFP_TEST_UNLIMITED_BUILD=1. The original timeout=0 command must fail a
two-second Pure theory with a ROOT-local one-second timer; the unlimited command
must finish it. Neither case generates or runs an AFP program. Each attempt is
retained under full/tooling, including the expected legacy timeout diagnostic.
"""
import os
import unittest
import uuid

import afp_common as common
import full


@unittest.skipUnless(os.environ.get("AFP_TEST_UNLIMITED_BUILD") == "1",
                     "opt-in native Isabelle build regression")
class UnlimitedBuildIntegration(unittest.TestCase):
    def test_root_local_timer_is_disabled_without_removing_the_root_setting(self):
        # Use distinct sessions so the successful case cannot reuse a heap or
        # database from the deliberately bounded case. The build lock also
        # prevents this small test from racing a running AFP proof build.
        base = common.HERE / "full"
        work = full.next_attempt(base / "tooling/unlimited-build-fixture")
        args = common.arguments(__doc__).parse_args([
            "--timeout", "0", "--max-heap-mb", "512", "--java-heap-mb", "512",
            "--min-available-mb", "512"])
        env, metadata = common.environment(args)
        token = uuid.uuid4().hex[:12]
        sessions = {}
        for mode in ("legacy", "unlimited"):
            session = "AFP_Timer_" + mode + "_" + token
            sessions[mode] = session
            directory = work / mode
            directory.mkdir()
            (directory / "Slow.thy").write_text(
                'theory Slow imports Pure begin\n'
                'ML \\<open>OS.Process.sleep (Time.fromSeconds 2); '
                'writeln "timer-probe-complete"\\<close>\nend\n')
        (work / "ROOT").write_text("\n".join(
            'session ' + session + ' in "' + mode + '" = Pure +\n'
            '  options [timeout = 1]\n  theories Slow\n'
            for mode, session in sessions.items()))
        outcomes = {}
        with common.build_lock():
            for mode, session in sessions.items():
                options = common.build_options(args)
                if mode == "legacy":
                    # Reproduce the former command exactly at the relevant
                    # option: its ROOT timeout wins over timeout=0.
                    index = options.index("timeout_build=false")
                    del options[index - 1:index + 1]
                    options += ["-o", "timeout_build=true"]
                outcomes[mode] = common.command(
                    [args.isabelle, "build", "-v", *options, "-d", str(work), session],
                    work / (mode + ".log"), args, env)
                common.write_json(work / "result.json",
                    {"environment": metadata, "root_timeout_seconds": 1,
                     "theory_delay_seconds": 2, "outcomes": outcomes})
        legacy = (work / "legacy.log").read_text()
        unlimited = (work / "unlimited.log").read_text()
        self.assertEqual(outcomes["legacy"]["status"], "failed", legacy)
        self.assertIn("Timeout", legacy)
        self.assertEqual(outcomes["unlimited"]["status"], "passed", unlimited)
        # The build console suppresses ordinary theory messages. Successful
        # completion plus the elapsed delay proves the ROOT timer was bypassed.
        self.assertGreaterEqual(outcomes["unlimited"]["seconds"], 2)
        self.assertNotIn("*** Timeout", unlimited)
        common.write_json(base / "unlimited-build-validation.json",
            {"status": "passed", "checked": common.timestamp(),
             "directory": common.relative(work), "outcomes": outcomes,
             "checks": ["ROOT-local timer overrides legacy timeout=0",
                        "unlimited build explicitly disables the internal timer",
                        "original ROOT timeout retained",
                        "generated programs not executed"]})


if __name__ == "__main__":
    unittest.main()
