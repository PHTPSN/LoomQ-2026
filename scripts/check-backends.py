#!/usr/bin/env python3
"""Run one real local shot through each selected vendor SDK environment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from starter_kit.adapter import run


HEALTH_QASM = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
measure q[0] -> c[0];'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify LoomQ local backends")
    parser.add_argument(
        "backends",
        nargs="*",
        choices=("spinq", "originq", "braket"),
        default=("spinq", "originq", "braket"),
    )
    args = parser.parse_args()
    for target in args.backends:
        result = run(HEALTH_QASM, target, 1)
        if sum(result["counts"].values()) != 1:
            raise RuntimeError("%s backend returned an invalid health result" % target)
        print("Backend ready: %s (%s)" % (target, result["backend"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
