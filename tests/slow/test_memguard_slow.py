"""Slow memory-guard test (Wave M; part of G11) per design_testing_and_validation.md §2."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.slow
def test_slow_memguard_two_processes_serialised(tmp_path: Path) -> None:
    """Two real processes each run guard('flux') around a 20 s dummy child.

    Using the real sysctl reader and the real lock dir:
    - Admitted intervals must not overlap.
    - Both memguard log lines must be present.
    """
    log1 = tmp_path / "proc1.log"
    log2 = tmp_path / "proc2.log"
    timestamps1 = tmp_path / "ts1.txt"
    timestamps2 = tmp_path / "ts2.txt"

    # Child script that runs guard("flux") with stage_log around a 20s dummy sleep
    script = """
import sys, time, subprocess
from pathlib import Path
from animated_infographics.memguard import guard

log_path = Path(sys.argv[1])
ts_path = Path(sys.argv[2])

with guard("flux", stage_log=log_path):
    t_start = time.time()
    ts_path.write_text(f"{t_start}\\n", encoding="utf-8")
    # 20 s dummy child
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
    proc.wait()
    t_end = time.time()
    ts_path.write_text(f"{t_start},{t_end}\\n", encoding="utf-8")
"""
    runner_py = tmp_path / "run_slow_guard.py"
    runner_py.write_text(script, encoding="utf-8")

    # Start both processes concurrently using real environment
    p1 = subprocess.Popen([sys.executable, str(runner_py), str(log1), str(timestamps1)])
    # Small offset so p1 enters first and contends with p2
    time.sleep(0.5)
    p2 = subprocess.Popen([sys.executable, str(runner_py), str(log2), str(timestamps2)])

    # Wait for both to finish (approx 40-45 s)
    p1.wait(timeout=60.0)
    p2.wait(timeout=60.0)

    assert p1.returncode == 0, f"Process 1 failed with returncode {p1.returncode}"
    assert p2.returncode == 0, f"Process 2 failed with returncode {p2.returncode}"

    # Verify timestamps
    assert timestamps1.is_file()
    assert timestamps2.is_file()

    t1_text = timestamps1.read_text(encoding="utf-8").strip()
    t2_text = timestamps2.read_text(encoding="utf-8").strip()
    t1_start, t1_end = [float(x) for x in t1_text.split(",")]
    t2_start, t2_end = [float(x) for x in t2_text.split(",")]

    # Intervals must not overlap: p1 finishes before p2 starts or vice versa
    no_overlap = (t1_end <= t2_start) or (t2_end <= t1_start)
    assert no_overlap, (
        f"Admitted intervals overlapped: p1=({t1_start}, {t1_end}), p2=({t2_start}, {t2_end})"
    )

    # Both memguard log lines must be present
    assert log1.is_file(), "Process 1 log file missing"
    assert log2.is_file(), "Process 2 log file missing"
    log1_content = log1.read_text(encoding="utf-8")
    log2_content = log2.read_text(encoding="utf-8")

    assert "memguard step=flux" in log1_content, f"Log 1 missing memguard line: {log1_content}"
    assert "memguard step=flux" in log2_content, f"Log 2 missing memguard line: {log2_content}"
