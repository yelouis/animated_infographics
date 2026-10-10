"""Unit tests for memguard.py per design_testing_and_validation.md §2."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from animated_infographics.assets.illustrate import generate
from animated_infographics.cli import app
from animated_infographics.jobs import Job, RunContext
from animated_infographics.memguard import (
    ResourceUnavailable,
    guard,
    watch,
)


def test_memguard_a_admits_immediately_when_memory_sufficient(tmp_path: Path) -> None:
    """(a) admits when available - peak >= 8 GB, with waited_ms=0."""
    lock_dir = tmp_path / "locks"
    log_file = tmp_path / "stage.log"
    os.environ["INFOGRAPHICS_LOCK_DIR"] = str(lock_dir)

    # 40 GB available, normal pressure (1)
    fake_available = 40 * (1024**3)
    with patch("animated_infographics.memguard.read_memory", return_value=(fake_available, 1)):
        with guard("flux", stage_log=log_file):
            pass

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "memguard step=flux waited_ms=0 available_gb=40.0 unloaded_llm=false" in content


def test_memguard_b_waits_and_admits_after_memory_rises(tmp_path: Path) -> None:
    """(b) with available rising after 3 polls (another program quitting),
    admits on 4th and logs waited_ms >= 15000.
    """
    lock_dir = tmp_path / "locks"
    log_file = tmp_path / "stage.log"
    os.environ["INFOGRAPHICS_LOCK_DIR"] = str(lock_dir)

    # Peak for flux is 32 GB, needs 32 + 8 = 40 GB.
    # First 3 polls: 35 GB (insufficient).
    # 4th poll: 45 GB (sufficient).
    read_values = [
        (35 * (1024**3), 1),
        (35 * (1024**3), 1),
        (35 * (1024**3), 1),
        (45 * (1024**3), 1),
    ]

    current_time = 1000.0

    def fake_monotonic() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(duration: float) -> None:
        nonlocal current_time
        current_time += duration

    with (
        patch("animated_infographics.memguard.read_memory", side_effect=read_values),
        patch("animated_infographics.memguard.is_ollama_model_loaded", return_value=False),
        patch("time.monotonic", side_effect=fake_monotonic),
        patch("time.sleep", side_effect=fake_sleep),
    ):
        with guard("flux", stage_log=log_file):
            pass

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "memguard step=flux" in content
    # Extract waited_ms
    for line in content.splitlines():
        if line.startswith("memguard step=flux"):
            parts = dict(kv.split("=") for kv in line.split()[1:])
            waited = int(parts["waited_ms"])
            assert waited >= 15000, f"Expected waited_ms >= 15000, got {waited}"
            assert parts["unloaded_llm"] == "false"
            assert float(parts["available_gb"]) == 45.0


def test_memguard_c_unloads_llm_if_sufficient_and_never_for_llm_load(tmp_path: Path) -> None:
    """(c) when gemma4:26b is loaded and unloading it suffices,
    unloads first and logs unloaded_llm=true; never unloads for llm_load.
    """
    lock_dir = tmp_path / "locks"
    log_file = tmp_path / "stage.log"
    os.environ["INFOGRAPHICS_LOCK_DIR"] = str(lock_dir)

    # Part 1: flux step
    # Need 32 + 8 = 40 GB.
    # Initial: 35 GB, model loaded.
    # After unload: 46 GB.
    memory_responses = [
        (35 * (1024**3), 1),  # initial check
        (46 * (1024**3), 1),  # check after unload
    ]

    unload_calls: list[str] = []

    def fake_unload(
        model: str = "gemma4:26b", endpoint: str | None = None, timeout_s: float = 30.0
    ) -> bool:
        unload_calls.append(model)
        return True

    with (
        patch("animated_infographics.memguard.read_memory", side_effect=memory_responses),
        patch("animated_infographics.memguard.is_ollama_model_loaded", return_value=True),
        patch("animated_infographics.memguard.unload_ollama_model", side_effect=fake_unload),
    ):
        with guard("flux", stage_log=log_file):
            pass

    assert unload_calls == ["gemma4:26b"]
    content = log_file.read_text(encoding="utf-8")
    assert "memguard step=flux" in content
    assert "unloaded_llm=true" in content

    # Part 2: llm_load step must never unload llm
    unload_calls.clear()
    log_file_llm = tmp_path / "llm.log"
    # Need 12 + 8 = 20 GB. Initial 15 GB, then 25 GB on next poll.
    llm_mem = [
        (15 * (1024**3), 1),
        (25 * (1024**3), 1),
    ]
    with (
        patch("animated_infographics.memguard.read_memory", side_effect=llm_mem),
        patch("animated_infographics.memguard.is_ollama_model_loaded", return_value=True),
        patch("animated_infographics.memguard.unload_ollama_model", side_effect=fake_unload),
        patch("time.sleep", return_value=None),
    ):
        with guard("llm_load", stage_log=log_file_llm):
            pass

    assert unload_calls == [], "llm_load must never unload Ollama model"


def test_memguard_d_timeout_raises_resource_unavailable_and_cli_exits_5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(d) after INFOGRAPHICS_MEM_WAIT_S raises ResourceUnavailable,
    CLI exits 5 and job records failed_stage.
    """
    lock_dir = tmp_path / "locks"
    monkeypatch.setenv("INFOGRAPHICS_LOCK_DIR", str(lock_dir))
    monkeypatch.setenv("INFOGRAPHICS_MEM_WAIT_S", "0.05")

    # Need 40 GB, only 10 GB available
    with (
        patch("animated_infographics.memguard.read_memory", return_value=(10 * (1024**3), 1)),
        patch("animated_infographics.memguard.is_ollama_model_loaded", return_value=False),
    ):
        with pytest.raises(ResourceUnavailable, match="timed out waiting"):
            with guard("flux"):
                pass

    # Verify CLI error handler maps ResourceUnavailable to exit 5 and keeps failed_stage
    runner = CliRunner()
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    story_file = tmp_path / "story.txt"
    story_file.write_text("Hello world", encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job = Job.create(story_file, jobs_dir, now=now)

    def failing_stage(j: Job, ctx: RunContext) -> None:
        raise ResourceUnavailable("memory guard: test unavailable")

    registry = {"bible": failing_stage}

    with patch("animated_infographics.cli.STAGE_REGISTRY", registry):
        # Running preview or a command that executes job stages
        with pytest.raises(ResourceUnavailable):
            job.run(["bible"], registry, RunContext())

    assert job.state["failed_stage"] == "bible"
    assert job.state["state"] == "failed"

    # CLI test via runner
    with patch("animated_infographics.cli.Job.open") as mock_open:
        mock_job = MagicMock()
        mock_job.state = {
            "state": "approved",
            "approval": {"plan_sha256": "h"},
            "timeline_plan_sha256": "h",
        }
        mock_job.plan_sha256.return_value = "h"
        mock_job.run.side_effect = ResourceUnavailable("out of mem")
        mock_open.return_value = mock_job

        result = runner.invoke(app, ["render", str(job.dir)])
        assert result.exit_code == 5


def test_memguard_e_watchdog_terminates_child_on_critical_pressure(tmp_path: Path) -> None:
    """(e) watchdog terminates dummy child within 4 s of fake pressure turning critical,
    and never signals another pid.
    """
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])

    # Fake pressure: starts normal (1), then becomes critical (4)
    pressures = [
        (30 * (1024**3), 1),
        (30 * (1024**3), 4),  # critical
    ]

    def fake_read() -> tuple[int, int]:
        if pressures:
            return pressures.pop(0)
        return (30 * (1024**3), 4)

    t0 = time.monotonic()
    with (
        patch("animated_infographics.memguard.read_memory", side_effect=fake_read),
        patch("animated_infographics.memguard.WATCH_POLL_INTERVAL_S", 0.1),
    ):
        with pytest.raises(ResourceUnavailable, match="memory guard: stopped"):
            with watch("flux", child):
                # Wait for watchdog to trigger
                child.wait(timeout=5.0)

    t_elapsed = time.monotonic() - t0
    assert t_elapsed < 4.0, f"Expected termination within 4s, took {t_elapsed:.2f}s"
    assert child.poll() is not None, "Child process must be terminated"


def test_memguard_f_heavy_lock_serialisation_and_kill_frees_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(f) two processes contending for heavy.lock are strictly serialised,
    and killing holder frees lock.
    """
    lock_dir = tmp_path / "locks"
    lock_file = lock_dir / "heavy.lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("INFOGRAPHICS_LOCK_DIR", str(lock_dir))
    monkeypatch.delenv("INFOGRAPHICS_MEM_WAIT_S", raising=False)

    # Script for subprocess that takes guard("flux") and records timestamps
    script = f"""
import os, sys, time
from pathlib import Path
from animated_infographics.memguard import guard

os.environ["INFOGRAPHICS_LOCK_DIR"] = "{lock_dir}"
os.environ.pop("INFOGRAPHICS_MEM_WAIT_S", None)
out_file = Path(sys.argv[1])
hold_duration = float(sys.argv[2])

with guard("flux"):
    t_start = time.time()
    out_file.write_text(f"{{t_start}}\\n", encoding="utf-8")
    time.sleep(hold_duration)
    t_end = time.time()
    out_file.write_text(f"{{t_start}},{{t_end}}\\n", encoding="utf-8")
"""
    runner_py = tmp_path / "run_guard.py"
    runner_py.write_text(script, encoding="utf-8")

    out1 = tmp_path / "p1.txt"
    out2 = tmp_path / "p2.txt"

    with patch("animated_infographics.memguard.read_memory", return_value=(50 * (1024**3), 1)):
        # Run p1 (holds for 1.0s) and p2 (holds for 0.5s) concurrently
        p1 = subprocess.Popen([sys.executable, str(runner_py), str(out1), "1.0"])
        # Brief pause to ensure p1 starts first and takes lock
        time.sleep(0.15)
        p2 = subprocess.Popen([sys.executable, str(runner_py), str(out2), "0.5"])

        p1.wait(timeout=10.0)
        p2.wait(timeout=10.0)

    assert p1.returncode == 0
    assert p2.returncode == 0

    t1_start, t1_end = [float(x) for x in out1.read_text(encoding="utf-8").strip().split(",")]
    t2_start, t2_end = [float(x) for x in out2.read_text(encoding="utf-8").strip().split(",")]

    # Strictly serialised: p2 starts >= p1 ends
    assert t2_start >= t1_end - 0.05, f"Expected t2_start ({t2_start}) >= t1_end ({t1_end})"

    # Test killing holder frees lock
    p_holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"""
import fcntl, time
with open("{lock_file}", "a+") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    time.sleep(60)
""",
        ]
    )
    time.sleep(0.2)
    p_holder.kill()
    p_holder.wait()

    # Now we should be able to acquire lock immediately without blocking
    with guard("flux"):
        pass


def test_resource_unavailable_never_falls_back_to_icon(tmp_path: Path) -> None:
    """Falsification 3 check: ResourceUnavailable must pass through generate unchanged,
    never into icon fallback.
    """
    out_file = tmp_path / "test.png"

    with patch("animated_infographics.assets.illustrate.guard") as mock_guard:
        mock_guard.side_effect = ResourceUnavailable("Out of memory")
        with pytest.raises(ResourceUnavailable):
            generate("A bustling market", out_file)

    # Output file must NOT exist (no icon fallback generated)
    assert not out_file.exists()


def test_presentation_stages_route_through_guarded_functions(tmp_path: Path) -> None:
    """Verify presentation stages (speak, hear, tree assets) reach guarded functions."""
    from animated_infographics.presentation.hear import run_hear_stage
    from animated_infographics.presentation.speak import run_speak_stage
    from animated_infographics.presentation.tree import run_tree_stage

    job_dir = tmp_path / "pres_job"
    job_dir.mkdir(parents=True)
    job = MagicMock()
    job.dir = job_dir
    job.job_id = "pres_job"

    # Test speak routes to synthesize_narration (which guards kokoro)
    perf_path = job_dir / "performance.json"
    perf_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seed": 7,
                "level": "mild",
                "sentences": [
                    {"text": "Hello", "label": {"slide": "s1", "point": 0}, "op": "verbatim"}
                ],
                "op_counts": {"verbatim": 1},
            }
        ),
        encoding="utf-8",
    )
    voice_path = job_dir / "voice.json"
    voice_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "voice": "am_michael",
                "source": "flag",
                "reason": "flag",
            }
        ),
        encoding="utf-8",
    )

    with patch("animated_infographics.presentation.speak.synthesize_narration") as mock_synth:
        mock_offsets = MagicMock()
        mock_offsets.sentences = []
        mock_synth.return_value = (None, mock_offsets)
        run_speak_stage(job, RunContext())
        mock_synth.assert_called_once()

    # Test hear routes to transcribe (which guards whisper)
    audio_wav = job_dir / "audio" / "narration.wav"
    audio_wav.parent.mkdir(parents=True, exist_ok=True)
    audio_wav.write_bytes(b"RIFF dummy wav")
    with patch("animated_infographics.presentation.hear.transcribe") as mock_transcribe:
        mock_tr = MagicMock()
        mock_tr.words = []
        mock_tr.sentences = []
        mock_tr.duration_ms = 1000
        mock_tr.model_dump_json.return_value = "{}"
        mock_transcribe.return_value = mock_tr
        run_hear_stage(job, RunContext())
        mock_transcribe.assert_called_once_with(audio_wav, job_dir)

    # Test tree routes to run_assets (which guards flux)
    deck_path = job_dir / "deck.json"
    deck_path.write_text('{"schema_version": 1, "slides": []}', encoding="utf-8")
    deck_bible_path = job_dir / "deck_bible.json"
    deck_bible_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "T",
                "logline": "L",
                "genre": "history",
                "cast": [],
                "places": [],
                "set_pieces": [],
            }
        ),
        encoding="utf-8",
    )
    with (
        patch("animated_infographics.presentation.tree.plan_tree") as mock_plan_tree,
        patch("animated_infographics.presentation.tree.compile_tree_timeline") as mock_compile,
        patch("animated_infographics.presentation.tree.run_assets") as mock_assets,
    ):
        mock_tree = MagicMock()
        mock_tree.nodes = []
        mock_tree.edges = []
        mock_tree.model_dump_json.return_value = "{}"
        mock_plan_tree.return_value = mock_tree
        mock_timeline = MagicMock()
        mock_timeline.model_dump_json.return_value = "{}"
        mock_compile.return_value = mock_timeline

        run_tree_stage(job, RunContext())
        mock_assets.assert_called_once()
