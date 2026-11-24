#!/usr/bin/env python3
"""Install the pinned read-only interface and rebuild its actual dependency heaps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import afp_common as common
from afp import runtime_arguments
import native_patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = common.configure(args.config)
    options = common.arguments("patch heaps").parse_args(runtime_arguments(config))
    env, _ = common.environment(options)
    with common.experiment_lock(), common.build_lock():
        result = native_patch.apply(env["ISABELLE_HOME"])
        subprocess.run([options.isabelle, "build", "-b", *common.build_options(options),
                        "-d", str(common.PROJECT), "-d", str(options.afp / "thys"), "Rust", "Go"],
                       env=env, check=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
