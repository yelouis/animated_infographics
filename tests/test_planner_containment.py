"""Unit tests for planner crash containment (Item B3).

Per agent_execution_guide.md and design_testing_and_validation.md:
- generate_json( appears under src/animated_infographics/planner/ ONLY in llm.py.
- run_with_retries( call sites count is 5 after B3 (voice, bible, segment, select, props).
- select and props recover when the first attempt produces malformed JSON and succeed on attempt 2.
- A stub backend whose every reply is malformed/truncated makes select and props fall back safely;
  the storyboard completes and plan_report.json records fallback_level: 2.
"""

from pathlib import Path
from typing import Any

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.planner.props import plan_single_template_props, plan_storyboard
from animated_infographics.planner.select import plan_template_selection


def test_generate_json_only_in_llm_py() -> None:
    """Verify that backend.generate_json is never called directly outside llm.py."""
    planner_dir = (
        Path(__file__).resolve().parent.parent / "src" / "animated_infographics" / "planner"
    )
    violating_files: list[str] = []

    for py_path in planner_dir.glob("*.py"):
        if py_path.name == "llm.py":
            continue
        content = py_path.read_text(encoding="utf-8")
        if "generate_json(" in content:
            violating_files.append(py_path.name)

    assert not violating_files, (
        f"generate_json( called directly outside llm.py in: {violating_files}. "
        "All LLM calls in planner must go through run_with_retries."
    )


def test_run_with_retries_call_count() -> None:
    """Verify run_with_retries call sites count is 10 after G3 (9 in planner/, 1 in assets/)."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "animated_infographics"
    call_sites: list[str] = []

    for search_dir in [src_dir / "planner", src_dir / "assets"]:
        for py_path in sorted(search_dir.glob("*.py")):
            if py_path.name == "llm.py":
                continue
            lines = py_path.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines, start=1):
                if "run_with_retries(" in line:
                    call_sites.append(f"{py_path.name}:{idx}")

    assert len(call_sites) == 10, (
        "Expected 10 run_with_retries call sites "
        "(voice, bible, segment, select, props [2], text_check, director, license [2]), "
        f"got {len(call_sites)}: {call_sites}"
    )


class MockFlakyBackend:
    """Mock backend that raises ValueError on attempt 0 and succeeds on attempt 1."""

    def __init__(self, success_payload: dict[str, Any]) -> None:
        self.success_payload = success_payload
        self.calls = 0
        self.cache_hits = 0

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        if attempt == 0:
            raise ValueError("Truncated or malformed JSON from model")
        return self.success_payload


class MockFailingBackend:
    """Mock backend whose every reply fails with malformed JSON."""

    def __init__(self) -> None:
        self.calls = 0
        self.cache_hits = 0

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        raise ValueError("Unrecoverable malformed JSON")


def _make_sample_transcript_and_beats() -> tuple[Transcript, list[Beat], Bible]:
    words = [
        TranscriptWord(i=0, sentence_i=0, text="In", start_ms=0, end_ms=300),
        TranscriptWord(i=1, sentence_i=0, text="1919,", start_ms=350, end_ms=700),
        TranscriptWord(i=2, sentence_i=0, text="Boston", start_ms=750, end_ms=1100),
        TranscriptWord(i=3, sentence_i=0, text="flooded.", start_ms=1150, end_ms=1600),
        TranscriptWord(i=4, sentence_i=1, text="A", start_ms=1700, end_ms=1900),
        TranscriptWord(i=5, sentence_i=1, text="giant", start_ms=1950, end_ms=2300),
        TranscriptWord(i=6, sentence_i=1, text="wave", start_ms=2350, end_ms=2700),
        TranscriptWord(i=7, sentence_i=1, text="struck.", start_ms=2750, end_ms=3200),
    ]
    sentences = [
        TranscriptSentence(
            i=0,
            text="In 1919, Boston flooded.",
            start_ms=0,
            end_ms=1600,
            word_start=0,
            word_end=4,
            paragraph_i=0,
            is_title=False,
        ),
        TranscriptSentence(
            i=1,
            text="A giant wave struck.",
            start_ms=1700,
            end_ms=3200,
            word_start=4,
            word_end=8,
            paragraph_i=0,
            is_title=False,
        ),
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=3500,
        words=words,
        sentences=sentences,
    )
    beats = [
        Beat(
            i=0,
            start_ms=0,
            end_ms=1600,
            text="In 1919, Boston flooded.",
            word_start=0,
            word_end=4,
        ),
        Beat(
            i=1,
            start_ms=1700,
            end_ms=3200,
            text="A giant wave struck.",
            word_start=4,
            word_end=8,
        ),
    ]
    bible = Bible(
        schema_version=1,
        title="The Great Flood",
        logline="A disaster story.",
        genre="history",
        cast=[],
        places=[],
        set_pieces=[],
    )
    return transcript, beats, bible


def test_select_recovers_from_malformed_json_on_first_attempt() -> None:
    """Verify select retries and recovers when attempt 0 returns malformed JSON."""
    transcript, beats, bible = _make_sample_transcript_and_beats()
    valid_choices = {
        "choices": [{"beat_i": 1, "primary": "kinetic_quote", "alternate": "stat_callout"}]
    }
    backend = MockFlakyBackend(valid_choices)

    choices, repairs, calls, hits = plan_template_selection(transcript, beats, bible, backend)
    assert len(choices) == 2
    assert choices[0].primary == "title_card"
    assert choices[1].primary == "kinetic_quote"
    assert backend.calls == 2


def test_props_recovers_from_malformed_json_on_first_attempt() -> None:
    """Verify props retries and recovers when attempt 0 returns malformed JSON."""
    transcript, beats, bible = _make_sample_transcript_and_beats()
    valid_props = {
        "text": "A giant wave struck.",
        "emphasis": ["giant"],
        "attribution_cast_id": None,
    }
    backend = MockFlakyBackend(valid_props)
    prompt_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "animated_infographics"
        / "planner"
        / "prompts"
        / "props.md"
    )
    prompt_template = prompt_path.read_text(encoding="utf-8")

    scene, errs, attempts = plan_single_template_props(
        template_name="kinetic_quote",
        scene_id="s001",
        beat_i=1,
        beat=beats[1],
        prev_beat=beats[0],
        next_beat=None,
        transcript=transcript,
        bible=bible,
        backend=backend,
        prompt_template=prompt_template,
        compact_bible="",
    )

    assert scene is not None
    assert scene.template == "kinetic_quote"
    assert attempts == 2


def test_storyboard_containment_every_reply_malformed_falls_back() -> None:
    """Verify that when all replies are malformed, storyboard completes with fallback_level: 2."""
    transcript, beats, bible = _make_sample_transcript_and_beats()
    backend = MockFailingBackend()

    storyboard, plan_report = plan_storyboard(transcript, beats, bible, backend)

    assert len(storyboard.scenes) == len(beats)
    assert storyboard.scenes[0].template == "title_card"
    assert storyboard.scenes[1].template == "kinetic_quote"

    assert len(plan_report.scenes) == len(beats)
    assert plan_report.scenes[0].fallback_level == 0
    assert plan_report.scenes[1].fallback_level == 2
