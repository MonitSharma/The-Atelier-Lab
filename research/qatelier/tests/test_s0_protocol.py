from __future__ import annotations

import subprocess
import sys


def test_s0_preregistration_refuses_unlocked_execution():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research.qatelier.experiments.s0_reproduction.run",
            "--config",
            "research/qatelier/experiments/s0_reproduction/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "S0 execution blocked" in result.stderr or "S0 execution blocked" in result.stdout
