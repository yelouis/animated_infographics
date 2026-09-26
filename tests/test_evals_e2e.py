import json
import subprocess


def test_check_sync_cli_json():
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "animated_infographics.evals.e2e",
        "check-sync",
        "--mp4",
        "artifacts/smoke.mp4",
        "--timeline",
        "renderer/test-data/timeline_smoke.json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    assert "checked" in data
    assert "expected" in data
    assert "failures" in data
    assert data["checked"] == 2
    assert data["expected"] == 2
    assert data["failures"] == []


def test_measure_audio_rms_cli():
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "animated_infographics.evals.e2e",
        "measure-audio-rms",
        "--mp4",
        "artifacts/smoke.mp4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    assert "duration" in data
    assert "start_s" in data
    assert "end_s" in data
    assert "rms_dbfs" in data


def test_check_sync_falsification_skip_boundary():
    # Skipping a boundary must cause check-sync to return exit code 1
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "animated_infographics.evals.e2e",
        "check-sync",
        "--mp4",
        "artifacts/smoke.mp4",
        "--timeline",
        "renderer/test-data/timeline_smoke.json",
        "--skip-boundary",
        "1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["checked"] == 1
    assert data["expected"] == 2


def test_measure_audio_rms_min_rms_failure():
    # If min-rms is set higher than actual RMS, must return exit code 1
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "animated_infographics.evals.e2e",
        "measure-audio-rms",
        "--mp4",
        "artifacts/smoke.mp4",
        "--min-rms",
        "0.0",  # impossible to exceed 0 dBFS
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 1
