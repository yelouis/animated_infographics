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


def test_verify_e2e_scenes_checks_date_junk_era(tmp_path):
    from animated_infographics.evals.verify_e2e_scenes import verify_job_scenes

    job_dir = tmp_path / "test_job"
    job_dir.mkdir()

    plan_report = {"scenes": [], "rule_repairs": []}
    (job_dir / "plan_report.json").write_text(json.dumps(plan_report), encoding="utf-8")

    beats = [{"i": 0, "text": "March 3rd was her birthday."}]
    (job_dir / "beats.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")

    transcript = {"sentences": [{"text": "March 3rd was her birthday."}]}
    (job_dir / "transcript.json").write_text(json.dumps(transcript), encoding="utf-8")

    # 1. Failing job: has date stat, junk text, and invented era stamp
    storyboard_fail = {
        "scenes": [
            {
                "id": "s000",
                "beat_i": 0,
                "template": "stat_callout",
                "props": {
                    "value": 3.0,
                    "decimals": 0,
                    "display_scale": "none",
                    "suffix": "",
                },
            },
            {
                "id": "s001",
                "beat_i": 0,
                "template": "comparison",
                "props": {
                    "a": {"heading": "Side A", "points": ["Icon: Bullet"]},
                    "b": {"heading": "Side B", "points": ["Normal"]},
                },
            },
            {
                "id": "s002",
                "beat_i": 0,
                "template": "location",
                "props": {
                    "place_id": "p1",
                    "era_label": "Present Day",
                },
            },
        ]
    }
    (job_dir / "storyboard.json").write_text(json.dumps(storyboard_fail), encoding="utf-8")

    res = verify_job_scenes(job_dir)
    assert res["date_stats"] == 1
    assert res["junk_text"] == 1
    assert res["invented_era_stamps"] == 1
    assert not res["passed"]

    # 2. Clean job: no date stats, no junk text, valid era stamp (or null)
    storyboard_pass = {
        "scenes": [
            {
                "id": "s000",
                "beat_i": 0,
                "template": "kinetic_quote",
                "props": {
                    "text": "March 3rd was her birthday.",
                    "emphasis": [],
                    "attribution_cast_id": None,
                },
            },
            {
                "id": "s001",
                "beat_i": 0,
                "template": "location",
                "props": {
                    "place_id": "p1",
                    "era_label": None,
                },
            },
        ]
    }
    (job_dir / "storyboard.json").write_text(json.dumps(storyboard_pass), encoding="utf-8")

    res_clean = verify_job_scenes(job_dir)
    assert res_clean["date_stats"] == 0
    assert res_clean["junk_text"] == 0
    assert res_clean["invented_era_stamps"] == 0
    assert res_clean["passed"]
