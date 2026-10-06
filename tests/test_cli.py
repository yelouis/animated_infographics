"""Integration tests for the Animated Infographics CLI and review gate."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from animated_infographics.cli import app, set_stage_registry
from animated_infographics.jobs import Job, RunContext

runner = CliRunner()


@pytest.fixture
def fake_stages() -> dict[str, Any]:
    def fake_ingest(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "kind": "text",
            "source": "test.txt",
            "title": "Story Title",
            "paragraphs": [
                "Sentence one is here. Sentence two is here. Sentence three is here. "
                "Sentence four is here. Sentence five is here. Sentence six is here. "
                "Sentence seven is here. Sentence eight is here."
            ],
            "word_count": 400,
            "perturb": ctx.perturb,
            "seed": ctx.seed,
            "tiebreak": ctx.tiebreak,
        }
        (j.dir / "ingest.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_voice(j: Job, ctx: RunContext) -> None:
        (j.dir / "voice.json").write_text('{"voice":"am_michael"}', encoding="utf-8")

    def _make_fake_transcript(src: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source": src,
            "audio_path": "audio/narration.wav",
            "duration_ms": 1000,
            "words": [
                {"i": 0, "sentence_i": 0, "text": "Scene", "start_ms": 0, "end_ms": 500},
                {"i": 1, "sentence_i": 0, "text": "one", "start_ms": 500, "end_ms": 1000},
            ],
            "sentences": [
                {
                    "i": 0,
                    "paragraph_i": 0,
                    "text": "Scene one",
                    "start_ms": 0,
                    "end_ms": 1000,
                    "word_start": 0,
                    "word_end": 2,
                    "is_title": True,
                }
            ],
        }

    def fake_narrate(j: Job, ctx: RunContext) -> None:
        (j.dir / "narration.json").write_text("{}", encoding="utf-8")
        (j.dir / "audio" / "narration.wav").write_bytes(b"RIFFdummywav")
        (j.dir / "transcript.json").write_text(
            json.dumps(_make_fake_transcript("tts")), encoding="utf-8"
        )

    def fake_transcribe(j: Job, ctx: RunContext) -> None:
        (j.dir / "transcript.json").write_text(
            json.dumps(_make_fake_transcript("asr")), encoding="utf-8"
        )

    def fake_bible(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "title": "Test Title",
            "logline": "Test logline",
            "genre": "history",
            "cast": [],
            "places": [],
            "set_pieces": [],
        }
        (j.dir / "bible.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_segment(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "beats": [
                {
                    "i": 0,
                    "word_start": 0,
                    "word_end": 2,
                    "start_ms": 0,
                    "end_ms": 1000,
                    "text": "Scene one",
                }
            ],
        }
        (j.dir / "beats.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_storyboard(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "aspect": "9:16",
            "scenes": [
                {
                    "id": "s000",
                    "beat_i": 0,
                    "template": "title_card",
                    "props": {"title": "Scene 1"},
                }
            ],
        }
        (j.dir / "storyboard.json").write_text(json.dumps(data), encoding="utf-8")
        (j.dir / "plan_report.json").write_text("{}", encoding="utf-8")

    def fake_assets(j: Job, ctx: RunContext) -> None:
        (j.dir / "assets" / "manifest.json").write_text("{}", encoding="utf-8")
        (j.dir / "assets" / "images" / "dummy.png").write_bytes(b"dummy")

    def fake_compile(j: Job, ctx: RunContext) -> None:
        (j.dir / "timeline.json").write_text("{}", encoding="utf-8")

    def fake_preview(j: Job, ctx: RunContext) -> None:
        (j.dir / "preview" / "contact_sheet.png").write_bytes(b"png")
        (j.dir / "preview" / "storyboard.md").write_text("# Preview", encoding="utf-8")

    def fake_render(j: Job, ctx: RunContext) -> None:
        (j.dir / "out" / "final.mp4").write_bytes(b"mp4")

    def fake_director(j: Job, ctx: RunContext) -> None:
        pass

    def fake_deck(j: Job, ctx: RunContext) -> None:
        titles = ["Slide One", "Slide Two", "Slide Three", "Slide Four"]
        data = {
            "schema_version": 1,
            "slides": [
                {
                    "id": f"d{i}",
                    "title": titles[i - 1],
                    "sentence_ids": [2 * i - 1, 2 * i],
                    "points": [
                        {"text": "Point A", "sentence_ids": [2 * i - 1]},
                        {"text": "Point B", "sentence_ids": [2 * i]},
                    ],
                }
                for i in range(1, 5)
            ],
        }
        (j.dir / "deck.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_deck_bible(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "title": "Test Title",
            "logline": "Test logline",
            "genre": "history",
            "cast": [],
            "places": [],
            "set_pieces": [],
        }
        (j.dir / "deck_bible.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_tree(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "nodes": [],
            "edges": [],
        }
        (j.dir / "tree.json").write_text(json.dumps(data), encoding="utf-8")
        (j.dir / "timeline.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "duration_frames": 150,
                    "fps": 30,
                    "width": 1080,
                    "height": 1920,
                    "plan_sha256": "fake",
                    "cast": {},
                    "places": {},
                    "set_pieces": {},
                    "scenes": [],
                    "captions": {"pages": []},
                    "audio": {"narration": {"src": "points.wav"}, "music": None, "sfx": []},
                    "debug": {"lead_ms": 0, "tail_ms": 0, "total_ms": 5000},
                }
            ),
            encoding="utf-8",
        )

    def fake_perform(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "seed": 42,
            "level": "mild",
            "sentences": [
                {
                    "text": "Point A",
                    "label": {"slide": "d1", "point": 0},
                    "op": "verbatim",
                    "source_sentence_id": 1,
                }
            ],
            "op_counts": {"verbatim": 1, "paraphrase": 0, "filler": 0, "adlib": 0, "back_ref": 0},
        }
        (j.dir / "performance.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_speak(j: Job, ctx: RunContext) -> None:
        (j.dir / "audio").mkdir(parents=True, exist_ok=True)
        (j.dir / "audio" / "narration.wav").write_bytes(b"RIFFdummywav")
        (j.dir / "speak_timing.json").write_text(
            json.dumps([{"sentence_i": 0, "start_ms": 0, "end_ms": 1000}]),
            encoding="utf-8",
        )

    def fake_hear(j: Job, ctx: RunContext) -> None:
        (j.dir / "heard.json").write_text(
            json.dumps(_make_fake_transcript("asr")),
            encoding="utf-8",
        )

    def fake_follow(j: Job, ctx: RunContext) -> None:
        data = {
            "schema_version": 1,
            "commits": [
                {
                    "node_id": "d1_sec",
                    "at_ms": 0,
                    "decision_ms": 0,
                    "compute_ms": 0,
                    "score": 0.0,
                }
            ],
            "holds": [],
        }
        (j.dir / "playback.json").write_text(json.dumps(data), encoding="utf-8")

    def fake_compose(j: Job, ctx: RunContext) -> None:
        pass

    registry = {
        "ingest": fake_ingest,
        "voice": fake_voice,
        "narrate": fake_narrate,
        "transcribe": fake_transcribe,
        "bible": fake_bible,
        "segment": fake_segment,
        "director": fake_director,
        "storyboard": fake_storyboard,
        "assets": fake_assets,
        "compile": fake_compile,
        "deck": fake_deck,
        "deck_bible": fake_deck_bible,
        "tree": fake_tree,
        "perform": fake_perform,
        "speak": fake_speak,
        "hear": fake_hear,
        "follow": fake_follow,
        "compose": fake_compose,
        "preview": fake_preview,
        "render": fake_render,
    }
    set_stage_registry(registry)
    return registry


def test_cli_prevalidation_rejections(tmp_path: Path) -> None:
    """Verify bad inputs and invalid option combinations exit 2 with no job directory created."""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # 1. Missing input file
    res = runner.invoke(app, ["new", str(tmp_path / "missing.txt"), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []

    # 2. Unsupported extension
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy", encoding="utf-8")
    res = runner.invoke(app, ["new", str(pdf_file), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []

    # 3. Audio input with --voice
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"RIFF")
    res = runner.invoke(
        app, ["new", str(wav_file), "--voice", "af_heart", "--jobs-dir", str(jobs_dir)]
    )
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []

    # 4. Text input with invalid voice
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello world", encoding="utf-8")
    res = runner.invoke(
        app, ["new", str(txt_file), "--voice", "invalid_voice", "--jobs-dir", str(jobs_dir)]
    )
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []

    # 5. Non-existent music file
    res = runner.invoke(
        app,
        [
            "new",
            str(txt_file),
            "--music",
            str(tmp_path / "nonexistent.wav"),
            "--jobs-dir",
            str(jobs_dir),
        ],
    )
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []

    # 6. Non-existent SFX dir
    res = runner.invoke(
        app,
        [
            "new",
            str(txt_file),
            "--sfx-dir",
            str(tmp_path / "nonexistent_sfx"),
            "--jobs-dir",
            str(jobs_dir),
        ],
    )
    assert res.exit_code == 2
    assert list(jobs_dir.iterdir()) == []


def test_cli_new_text_and_audio(tmp_path: Path, fake_stages: Any) -> None:
    """Verify new command runs through preview and prints required paths."""
    jobs_dir = tmp_path / "jobs"
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Some script text", encoding="utf-8")

    res = runner.invoke(app, ["new", str(txt_file), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    assert "preview/contact_sheet.png" in res.stdout
    assert "preview/storyboard.md" in res.stdout
    assert "bible.json" in res.stdout
    assert "storyboard.json" in res.stdout

    created_jobs = list(jobs_dir.iterdir())
    assert len(created_jobs) == 1
    job_dir = created_jobs[0]
    job = Job(job_dir)
    assert job.state["state"] == "awaiting_review"
    assert (
        job.state["plan_sha256"]
        == job.state["preview_plan_sha256"]
        == job.state["timeline_plan_sha256"]
    )
    assert job.state["approval"] is None

    # Audio input
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"RIFF")
    res_audio = runner.invoke(app, ["new", str(wav_file), "--jobs-dir", str(jobs_dir)])
    assert res_audio.exit_code == 0
    assert len(list(jobs_dir.iterdir())) == 2


def test_cli_refusal_cases(tmp_path: Path, fake_stages: Any) -> None:
    """Verify all refusal conditions in architecture §5 exit with code 3."""
    jobs_dir = tmp_path / "jobs"
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Sample text", encoding="utf-8")

    res = runner.invoke(app, ["new", str(txt_file), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job_dir = list(jobs_dir.iterdir())[0]

    # 1. approve on job not awaiting_review (simulate state=planning)
    job = Job(job_dir)
    job.state["state"] = "planning"
    job.save_state()
    res = runner.invoke(app, ["approve", str(job_dir), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 3

    # Reset state to awaiting_review
    job.state["state"] = "awaiting_review"
    job.save_state()

    # 2. approve when preview_plan_sha256 != plan_sha256(now) (e.g. edited bible)
    bible_path = job_dir / "bible.json"
    bible_data = json.loads(bible_path.read_text(encoding="utf-8"))
    bible_data["title"] = "Edited Title Before Preview"
    bible_path.write_text(json.dumps(bible_data), encoding="utf-8")

    res = runner.invoke(app, ["approve", str(job_dir), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 3
    assert "plan changed since preview" in res.stderr

    # 3. render on job not approved (state is awaiting_review)
    res = runner.invoke(app, ["render", str(job_dir), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 3

    # 4. preview on job in state planning or failed
    job.state["state"] = "failed"
    job.save_state()
    res = runner.invoke(app, ["preview", str(job_dir), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 3

    # 5. preview validation failure on invalid edited storyboard (exit 2)
    job.state["state"] = "awaiting_review"
    job.save_state()
    sb_path = job_dir / "storyboard.json"
    sb_data = json.loads(sb_path.read_text(encoding="utf-8"))
    sb_data["scenes"][0]["id"] = "invalid_id_format"
    sb_path.write_text(json.dumps(sb_data), encoding="utf-8")

    res = runner.invoke(app, ["preview", str(job_dir), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 2
    assert "storyboard.json validation failed" in res.stderr


def test_cli_journey(tmp_path: Path, fake_stages: Any) -> None:
    """Verify journey: new -> approve -> edit -> render (3) -> preview -> approve -> render (0)."""
    jobs_dir = tmp_path / "jobs"
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Journey story script", encoding="utf-8")

    # Step 1: new
    res = runner.invoke(app, ["new", str(txt_file), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job_dir = list(jobs_dir.iterdir())[0]
    job_id = job_dir.name

    # Step 2: approve
    res = runner.invoke(app, ["approve", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job = Job(job_dir)
    assert job.state["state"] == "approved"
    assert job.state["approval"] is not None

    # Step 3: edit storyboard.json
    sb_path = job_dir / "storyboard.json"
    sb_data = json.loads(sb_path.read_text(encoding="utf-8"))
    sb_data["scenes"][0]["props"]["title"] = "Modified Title"
    sb_path.write_text(json.dumps(sb_data), encoding="utf-8")

    # Step 4: render -> MUST refuse with exit code 3
    res = runner.invoke(app, ["render", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 3
    assert "plan changed since approval" in res.stderr

    # Step 5: preview -> revalidates, clears approval, sets awaiting_review
    res = runner.invoke(app, ["preview", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job = Job(job_dir)
    assert job.state["state"] == "awaiting_review"
    assert job.state["approval"] is None

    # Step 6: approve
    res = runner.invoke(app, ["approve", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job = Job(job_dir)
    assert job.state["state"] == "approved"

    # Step 7: render -> MUST succeed with exit code 0
    res = runner.invoke(app, ["render", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job = Job(job_dir)
    assert job.state["state"] == "rendered"
    assert (job_dir / "out" / "final.mp4").is_file()


def test_cli_rerun_and_status(tmp_path: Path, fake_stages: Any) -> None:
    """Verify rerun invalidates pipeline from requested stage, and status prints state."""
    jobs_dir = tmp_path / "jobs"
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Rerun script", encoding="utf-8")

    res = runner.invoke(app, ["new", str(txt_file), "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job_id = list(jobs_dir.iterdir())[0].name

    # Check status
    res = runner.invoke(app, ["status", job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    assert f"Job: {job_id}" in res.stdout
    assert "State: awaiting_review" in res.stdout

    # Rerun with invalid stage -> exit 2
    res = runner.invoke(
        app, ["rerun", job_id, "--from", "invalid_stage", "--jobs-dir", str(jobs_dir)]
    )
    assert res.exit_code == 2

    # Rerun from segment -> exit 0, stops at awaiting_review
    res = runner.invoke(app, ["rerun", job_id, "--from", "segment", "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0
    job = Job(jobs_dir / job_id)
    assert job.state["state"] == "awaiting_review"


def test_present_sim_cli_flow(tmp_path: Path, fake_stages: Any) -> None:
    """Verify present-sim creates presentation job, preview re-validates,
    and invalid edit exits 2.
    """
    jobs_dir = tmp_path / "jobs"
    txt_file = tmp_path / "story.txt"
    txt_file.write_text(
        "Story Title\n\n"
        "Sentence one is here. Sentence two is here. Sentence three is here. "
        "Sentence four is here. Sentence five is here. Sentence six is here. "
        "Sentence seven is here. Sentence eight is here.",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        [
            "present-sim",
            str(txt_file),
            "--perturb",
            "mild",
            "--seed",
            "7",
            "--tiebreak",
            "none",
            "--jobs-dir",
            str(jobs_dir),
        ],
    )
    assert res.exit_code == 0
    job_dir = list(jobs_dir.iterdir())[0]
    job = Job(job_dir)
    assert job.kind == "presentation"
    assert job.state["state"] == "awaiting_review"

    # Check ingest.json recorded parameters
    ingest_data = json.loads((job_dir / "ingest.json").read_text(encoding="utf-8"))
    assert ingest_data["perturb"] == "mild"
    assert ingest_data["seed"] == 7
    assert ingest_data["tiebreak"] == "none"

    # preview command re-validates and passes
    res = runner.invoke(app, ["preview", job.job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 0

    # Human edit with invalid deck (skip sentence 3) -> preview must exit 2
    deck_path = job_dir / "deck.json"
    deck_data = json.loads(deck_path.read_text(encoding="utf-8"))
    deck_data["slides"][0]["sentence_ids"] = [1, 2]
    deck_data["slides"][1]["sentence_ids"] = [4, 5]  # skips sentence 3
    deck_path.write_text(json.dumps(deck_data), encoding="utf-8")

    res = runner.invoke(app, ["preview", job.job_id, "--jobs-dir", str(jobs_dir)])
    assert res.exit_code == 2
    assert "validation failed" in res.stderr.lower()
