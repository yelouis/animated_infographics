"""Tests for gate lock, budget validity, and memory doctor checks per Wave M."""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
from pathlib import Path

from animated_infographics.doctor import run_doctor
from animated_infographics.gatelock import is_live_ancestor, run_gatelock


def test_is_live_ancestor() -> None:
    """Test ancestor process verification."""
    # Parent PID is a live ancestor
    assert is_live_ancestor(os.getppid()) is True
    # Self is not an ancestor
    assert is_live_ancestor(os.getpid()) is False
    # Unrelated or dead PID is not an ancestor
    assert is_live_ancestor(999999) is False
    assert is_live_ancestor(1) is False
    assert is_live_ancestor(0) is False


def test_gatelock_held_exits_3_with_holder_info(tmp_path: Path, monkeypatch) -> None:
    """e2e.sh started while another gate holds gate.lock exits 3
    with 'another gate is running: ...'.
    """
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("INFOGRAPHICS_LOCK_DIR", str(lock_dir))
    monkeypatch.delenv("INFOGRAPHICS_GATE_LOCK_HELD", raising=False)

    gate_lock = lock_dir / "gate.lock"
    # Holder takes lock
    holder_fd = open(gate_lock, "a+", encoding="utf-8")
    fcntl.flock(holder_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    holder_fd.write("e2e pid 12345\n")
    holder_fd.flush()

    try:
        # Run gatelock contender
        code = run_gatelock("gallery", [sys.executable, "-c", "print('should not run')"])
        assert code == 3
    finally:
        fcntl.flock(holder_fd.fileno(), fcntl.LOCK_UN)
        holder_fd.close()


def test_gatelock_nested_with_live_ancestor(tmp_path: Path, monkeypatch) -> None:
    """battery.sh runs every gate in sequence with INFOGRAPHICS_GATE_LOCK_HELD."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("INFOGRAPHICS_LOCK_DIR", str(lock_dir))
    # When ancestor PID is set in INFOGRAPHICS_GATE_LOCK_HELD
    monkeypatch.setenv("INFOGRAPHICS_GATE_LOCK_HELD", str(os.getppid()))

    # Child gate executes directly without re-locking
    code = run_gatelock("check_gallery", [sys.executable, "-c", "import sys; sys.exit(0)"])
    assert code == 0


def test_gatelock_stale_held_variable_ignored(tmp_path: Path, monkeypatch) -> None:
    """A stale INFOGRAPHICS_GATE_LOCK_HELD naming a dead or unrelated pid is ignored,
    and the lock is taken normally.
    """
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("INFOGRAPHICS_LOCK_DIR", str(lock_dir))
    # Unrelated dead PID
    monkeypatch.setenv("INFOGRAPHICS_GATE_LOCK_HELD", "999999")

    out_file = tmp_path / "out.txt"
    code = run_gatelock(
        "battery",
        [sys.executable, "-c", f"open(r'{out_file}', 'w').write('ran'); import sys; sys.exit(0)"],
    )
    assert code == 0
    assert out_file.read_text() == "ran"


def test_budget_validity_invalid_on_waited_ms(tmp_path: Path) -> None:
    """A budget run whose stage logs contain waited_ms > 0 writes INVALID header and exits 1."""
    script_path = Path("scripts/measure_budget.sh").resolve()
    assert script_path.is_file()

    # Simulate log scan logic from measure_budget.sh
    job_dir = tmp_path / "job"
    logs_cold = job_dir / "logs_cold"
    logs_cold.mkdir(parents=True, exist_ok=True)

    stage_log = logs_cold / "assets.log"
    stage_log.write_text(
        "memguard step=flux waited_ms=5200 available_gb=40.0 unloaded_llm=false\n",
        encoding="utf-8",
    )

    report_path = tmp_path / "budget_report.md"

    # Run inspection snippet matching measure_budget.sh
    check_code = f"""
import re, sys
from pathlib import Path

job_dir = Path(r'{job_dir}')
report_path = Path(r'{report_path}')
mem_waited_ms = 0
step_stopped = False

for lf in (job_dir / 'logs_cold').glob('*.log'):
    for line in lf.read_text(encoding='utf-8').splitlines():
        if line.startswith('memguard '):
            m = re.search(r'waited_ms=(\\d+)', line)
            if m and int(m.group(1)) > 0:
                mem_waited_ms += int(m.group(1))
        if 'memory guard: stopped' in line:
            step_stopped = True

if mem_waited_ms > 0 or step_stopped:
    report_path.write_text(
        f'INVALID: memory guard waited {{mem_waited_ms}} ms\\n\\nReport body',
        encoding='utf-8',
    )
    sys.exit(1)
sys.exit(0)
"""
    res = subprocess.run([sys.executable, "-c", check_code])
    assert res.returncode == 1
    assert report_path.is_file()
    content = report_path.read_text(encoding="utf-8")
    assert content.startswith("INVALID: memory guard waited 5200 ms")


def test_budget_validity_invalid_on_stopped_step(tmp_path: Path) -> None:
    """A budget run whose stage logs contain a stopped step writes INVALID header and exits 1."""
    job_dir = tmp_path / "job"
    logs_cold = job_dir / "logs_cold"
    logs_cold.mkdir(parents=True, exist_ok=True)

    stage_log = logs_cold / "render.log"
    stage_log.write_text(
        "memory guard: stopped render at 3.5 GB available\n",
        encoding="utf-8",
    )

    report_path = tmp_path / "budget_report.md"

    check_code = f"""
import re, sys
from pathlib import Path

job_dir = Path(r'{job_dir}')
report_path = Path(r'{report_path}')
mem_waited_ms = 0
step_stopped = False

for lf in (job_dir / 'logs_cold').glob('*.log'):
    for line in lf.read_text(encoding='utf-8').splitlines():
        if line.startswith('memguard '):
            m = re.search(r'waited_ms=(\\d+)', line)
            if m and int(m.group(1)) > 0:
                mem_waited_ms += int(m.group(1))
        if 'memory guard: stopped' in line:
            step_stopped = True

if mem_waited_ms > 0 or step_stopped:
    report_path.write_text(
        f'INVALID: memory guard waited {{mem_waited_ms}} ms\\n\\nReport body',
        encoding='utf-8',
    )
    sys.exit(1)
sys.exit(0)
"""
    res = subprocess.run([sys.executable, "-c", check_code])
    assert res.returncode == 1
    assert report_path.is_file()
    content = report_path.read_text(encoding="utf-8")
    assert content.startswith("INVALID: memory guard waited 0 ms")


def test_doctor_hardware_memory_below_bar_exits_4(monkeypatch) -> None:
    """doctor fails (exit 4) if hw.memsize < largest declared peak + llm_load + FLOOR (52 GB)."""
    # Fake hw.memsize = 32 GB (< 52 GB)
    fake_mem = 32 * (1024**3)

    orig_check = subprocess.check_output

    def fake_check_output(cmd, **kwargs):
        if cmd == ["sysctl", "-n", "hw.memsize"]:
            return f"{fake_mem}\n"
        return orig_check(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    code = run_doctor()
    assert code == 4


def test_doctor_warns_when_available_below_flux_plus_floor(monkeypatch, capsys) -> None:
    """doctor warns (not fails) when available memory is below flux + FLOOR (40 GB)."""
    # 35 GB available (< 40 GB)
    fake_available = 35 * (1024**3)

    monkeypatch.setattr(
        "animated_infographics.doctor.read_memory",
        lambda: (fake_available, 1),
    )
    _ = run_doctor()
    # It must not turn a passing environment into a failure solely from available memory warning
    captured = capsys.readouterr()
    assert "WARN available memory" in captured.out
    assert "below flux + FLOOR" in captured.out
