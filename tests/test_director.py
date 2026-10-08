"""Tests for Creative Director and License stages.

Contracts and validation rules per design_styles.md §3.3, §3.4,
and design_testing_and_validation.md §2.
"""

from pathlib import Path
from typing import Any

import pytest

from animated_infographics.contracts.director import (
    DirectorPlan,
    MetaphorDirective,
)
from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    Place,
    SetPiece,
    Timeline,
    TimelineAudio,
    TimelineNarration,
    VoiceDecision,
)
from animated_infographics.planner.director import (
    DirectorContext,
    compute_director_counts,
    plan_director,
    validate_director_plan,
)
from animated_infographics.planner.license import (
    check_metaphor_license,
    run_license_checks,
)
from animated_infographics.preview import generate_storyboard_markdown


class StubLLMBackend:
    """Configurable stub backend for deterministic director and license testing."""

    def __init__(
        self, responses: list[dict[str, Any]] | None = None, fail_calls: bool = False
    ) -> None:
        self.responses = list(responses or [])
        self.fail_calls = fail_calls
        self.calls: int = 0
        self.cache_hits: int = 0
        self.model: str = "stub"

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, Any]] | None = None,
        schema: dict[str, Any],
        attempt: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        if self.fail_calls:
            raise RuntimeError("Backend failure simulation")
        if self.responses:
            return self.responses.pop(0)
        return {}


def _make_test_bible() -> Bible:
    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    return Bible(
        schema_version=1,
        title="The Old Library",
        genre="personal_story",
        logline="A mysterious book returned 50 years late.",
        cast=[
            CastMember(
                id="c1", name="June", role="narrator", is_narrator=True, color_slot=0, avatar=avatar
            ),
            CastMember(
                id="c2",
                name="Robert",
                role="visitor",
                is_narrator=False,
                color_slot=1,
                avatar=avatar,
            ),
        ],
        places=[
            Place(
                id="p1",
                name="Alder Creek",
                kind="real",
                geo_source="none",
                visual_description="A small quiet rural library town",
                icon="Buildings",
            ),
        ],
        set_pieces=[
            SetPiece(
                id="v1",
                name="The Ledger",
                visual_description="A thick leather bound library register",
                icon="BookOpen",
            )
        ],
    )


def _make_beats(n: int, quoted_indices: set[int] | None = None) -> list[Beat]:
    quoted = quoted_indices or set()
    beats: list[Beat] = []
    w_offset = 0
    ms_offset = 0
    for i in range(n):
        if i == 0:
            text = "Title beat: The Old Library."
        elif i in quoted:
            text = f'Beat {i}: He whispered, "Take this immediately."'
        else:
            text = f"Beat {i}: He walked into the quiet reading room."
        words_count = len(text.split())
        beats.append(
            Beat(
                i=i,
                word_start=w_offset,
                word_end=w_offset + words_count,
                start_ms=ms_offset,
                end_ms=ms_offset + 2500,
                text=text,
            )
        )
        w_offset += words_count
        ms_offset += 2500
    return beats


def _valid_n64_payload() -> dict[str, Any]:
    # n = 64: expected_metaphors = 5, expected_asides = 6
    return {
        "motifs": [
            {
                "id": "m1",
                "name": "the checkout card",
                "icon": "IdentificationCard",
                "set_piece_id": None,
                "appearances": [
                    {"beat_i": 5, "role": "plant"},
                    {"beat_i": 21, "role": "echo"},
                    {"beat_i": 52, "role": "payoff"},
                ],
            }
        ],
        "metaphors": [
            {
                "beat_i": 10,
                "image": "an antique brass hourglass with black sand",
                "label": "Time running out",
                "cast_ids": [],
            },
            {
                "beat_i": 18,
                "image": "two chairs facing each other across an empty table",
                "label": "Quiet distance",
                "cast_ids": ["c1", "c2"],
            },
            {
                "beat_i": 26,
                "image": "a solitary ship sailing under heavy dark clouds",
                "label": "Drifting apart",
                "cast_ids": [],
            },
            {
                "beat_i": 34,
                "image": "a stone wall with moss growing in the fissures",
                "label": "Silent barrier",
                "cast_ids": [],
            },
            {
                "beat_i": 42,
                "image": "an open birdcage sitting on a polished wooden desk",
                "label": "Sudden freedom",
                "cast_ids": [],
            },
        ],
        "asides": [
            {"beat_i": 8, "kind": "thought", "icon": "Coins", "text": None, "cast_id": "c2"},
            {"beat_i": 14, "kind": "label", "icon": None, "text": "Very overdue", "cast_id": None},
            {"beat_i": 22, "kind": "prop", "icon": "Cat", "text": None, "cast_id": None},
            {"beat_i": 30, "kind": "thought", "icon": "BookOpen", "text": None, "cast_id": "c1"},
            {"beat_i": 38, "kind": "label", "icon": None, "text": "Dusty shelves", "cast_id": None},
            {"beat_i": 46, "kind": "prop", "icon": "Key", "text": None, "cast_id": None},
        ],
    }


# ===========================================================================
# 1. Counts and Formulas
# ===========================================================================


def test_counts_formula() -> None:
    """Verify counts formula for metaphors and asides per §3.3."""
    # n = 64
    m64, a64 = compute_director_counts(64)
    assert m64 == 5
    assert a64 == 6

    # n = 24
    m24, a24 = compute_director_counts(24)
    assert m24 == 2  # max(2, min(5, 2))
    assert a24 == 2  # max(2, min(6, 2))

    # n = 120
    m120, a120 = compute_director_counts(120)
    assert m120 == 5  # clamped to 5
    assert a120 == 6  # clamped to 6


def test_validator_counts_check() -> None:
    """Test validator enforces exact counts for n=64."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    data = _valid_n64_payload()
    _, errors = validate_director_plan(data, ctx)
    assert errors == []

    # Fewer metaphors (4 instead of 5)
    bad_data = _valid_n64_payload()
    bad_data["metaphors"].pop()
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("expected exactly 5 metaphors" in e for e in errs)

    # Fewer asides (5 instead of 6)
    bad_data = _valid_n64_payload()
    bad_data["asides"].pop()
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("expected exactly 6 asides" in e for e in errs)

    # 0 motifs
    bad_data = _valid_n64_payload()
    bad_data["motifs"] = []
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("provide 1 to 3 motifs" in e for e in errs)


# ===========================================================================
# 2. Validator 1: beat_i in 1..n-1
# ===========================================================================


def test_validator_1_beat_range() -> None:
    """Beat 0 (title card) carries nothing; beat_i < 1 or >= n is rejected."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Metaphor on beat 0
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["beat_i"] = 0
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("beat 0 is invalid" in e for e in errs)

    # Aside on beat 64 (out of range, max is 63)
    bad_data = _valid_n64_payload()
    bad_data["asides"][0]["beat_i"] = 64
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("beat 64 is invalid" in e for e in errs)

    # Motif plant on beat 0
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["appearances"][0]["beat_i"] = 0
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("beat 0 is invalid" in e for e in errs)


# ===========================================================================
# 3. Validator 2: One directive per beat
# ===========================================================================


def test_validator_2_one_directive_per_beat() -> None:
    """At most one metaphor, one payoff, one aside; never both metaphor and payoff."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Two metaphors on beat 10
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][1]["beat_i"] = 10
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("beat 10 has 2 metaphors" in e for e in errs)

    # Metaphor and payoff on same beat (beat 52)
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["beat_i"] = 52
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("cannot have both a metaphor and a payoff" in e for e in errs)

    # Metaphor (beat 10) and aside (beat 10) on same beat is allowed!
    good_collision = _valid_n64_payload()
    good_collision["asides"][0]["beat_i"] = 10
    _, errs = validate_director_plan(good_collision, ctx)
    assert errs == []


# ===========================================================================
# 4. Validator 3: Motif structure & Falsification
# ===========================================================================


def test_validator_3_plant_before_payoff() -> None:
    """Payoff must come at least 3 beats after every plant."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Plant 2 beats before payoff (payoff 12, plant 10)
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["appearances"] = [
        {"beat_i": 10, "role": "plant"},
        {"beat_i": 12, "role": "payoff"},
    ]
    _, errs = validate_director_plan(bad_data, ctx)
    assert any(
        "the payoff (beat 12) must come at least 3 beats after every plant (beat 10)" in e
        for e in errs
    )

    # Plant 3 beats before payoff (payoff 13, plant 10) -> valid!
    good_data = _valid_n64_payload()
    good_data["motifs"][0]["appearances"] = [
        {"beat_i": 10, "role": "plant"},
        {"beat_i": 13, "role": "payoff"},
    ]
    _, errs = validate_director_plan(good_data, ctx)
    assert errs == []


def test_validator_3_falsification_payoff_before_plant() -> None:
    """Falsification test: payoff before plant must fail validation."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["appearances"] = [
        {"beat_i": 15, "role": "plant"},
        {"beat_i": 10, "role": "payoff"},
    ]
    _, errs = validate_director_plan(bad_data, ctx)
    assert any(
        "the payoff (beat 10) must come at least 3 beats after every plant (beat 15)" in e
        for e in errs
    )


def test_validator_3_echo_and_duplicates() -> None:
    """Echo after payoff is rejected; duplicate appearance on same beat rejected."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Echo on beat 55 when payoff is on beat 52
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["appearances"].append({"beat_i": 55, "role": "echo"})
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("echo on beat 55 must come before the payoff (beat 52)" in e for e in errs)

    # Duplicate appearance on beat 5
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["appearances"].append({"beat_i": 5, "role": "echo"})
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("duplicate appearance on beat 5" in e for e in errs)


# ===========================================================================
# 5. Validator 4: Quoted speech stays
# ===========================================================================


def test_validator_4_quoted_speech() -> None:
    """Metaphor or payoff may not sit on a beat containing quoted speech. Asides may."""
    bible = _make_test_bible()
    # Beat 10 and 52 contain quotes
    beats = _make_beats(64, quoted_indices={10, 52})
    ctx = DirectorContext(beats=beats, bible=bible)

    # Payload has metaphor on beat 10 and payoff on beat 52 -> both fail
    bad_data = _valid_n64_payload()
    _, errs = validate_director_plan(bad_data, ctx)
    assert any(
        "beat 10 contains quoted speech — metaphors may not sit on quoted beats" in e for e in errs
    )
    assert any(
        "payoff on beat 52 contains quoted speech — payoffs may not sit on quoted beats" in e
        for e in errs
    )

    # Aside on quoted beat is allowed
    aside_data = _valid_n64_payload()
    aside_data["metaphors"][0]["beat_i"] = 11  # unquoted
    aside_data["motifs"][0]["appearances"][2]["beat_i"] = 53  # unquoted
    aside_data["asides"][0]["beat_i"] = 10  # quoted beat 10
    _, errs = validate_director_plan(aside_data, ctx)
    assert errs == []


# ===========================================================================
# 6. Validator 5: Text checks, word caps, name leaks
# ===========================================================================


def test_validator_5_text_checks() -> None:
    """Text fields must satisfy caps, no digits, no quotes, and no cast/place name leaks."""
    bible = (
        _make_test_bible()
    )  # cast: June (c1), Robert (c2); place: Alder Creek; set_piece: The Ledger
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Motif name > 4 words
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["name"] = "this is five words long"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("words, limit 4" in e for e in errs)

    # Metaphor label > 3 words
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["label"] = "four whole words here"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("words, limit 3" in e for e in errs)

    # Digits in aside text
    bad_data = _valid_n64_payload()
    bad_data["asides"][1]["text"] = "Card 42"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("contains digits ('Card 42')" in e for e in errs)

    # Quotes in aside text
    bad_data = _valid_n64_payload()
    bad_data["asides"][1]["text"] = '"Overdue"'
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("contains quotation marks" in e for e in errs)

    # Name leak (cast member 'June' mentioned in metaphor label)
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["label"] = "June silent"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("contains the name 'June'" in e for e in errs)

    # Motif's own set piece name is allowed
    own_sp_data = _valid_n64_payload()
    own_sp_data["motifs"][0]["set_piece_id"] = "v1"
    own_sp_data["motifs"][0]["name"] = "The Ledger"
    _, errs = validate_director_plan(own_sp_data, ctx)
    assert not any("contains the name 'The Ledger'" in e for e in errs)


# ===========================================================================
# 7. Validator 6: Metaphor image checks
# ===========================================================================


def test_validator_6_image_checks() -> None:
    """Image must be <= 25 words, no quotes, and no writing/text requested."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Image > 25 words
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["image"] = "word " * 26
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("words, limit 25" in e for e in errs)

    # Image with quotation marks
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["image"] = 'a desk with a "note" on it'
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("contains quotation marks" in e for e in errs)

    # Image asking for writing / lettering
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["image"] = "a handwritten recipe card on the counter"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("asks for writing / lettering" in e for e in errs)


# ===========================================================================
# 8. Validator 7: IDs and Aside kinds
# ===========================================================================


def test_validator_7_entities_and_aside_kinds() -> None:
    """Entities must exist in bible; aside kinds require valid fields."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    ctx = DirectorContext(beats=beats, bible=bible)

    # Unknown set piece in motif
    bad_data = _valid_n64_payload()
    bad_data["motifs"][0]["set_piece_id"] = "v9"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("set piece 'v9' not found in bible" in e for e in errs)

    # Unknown cast member in metaphor
    bad_data = _valid_n64_payload()
    bad_data["metaphors"][0]["cast_ids"] = ["c99"]
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("cast 'c99' not found in bible" in e for e in errs)

    # Thought aside without cast_id
    bad_data = _valid_n64_payload()
    bad_data["asides"][0]["cast_id"] = None
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("thought aside requires a valid cast_id" in e for e in errs)

    # Thought aside without icon or text (I3)
    bad_data = _valid_n64_payload()
    bad_data["asides"][0]["icon"] = None
    bad_data["asides"][0]["text"] = None
    bad_data["asides"][0]["cast_id"] = "c1"
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("asides[0]: a thought needs an icon or text" in e for e in errs)

    # Prop aside without icon
    bad_data = _valid_n64_payload()
    bad_data["asides"][2]["icon"] = None
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("prop aside requires an icon" in e for e in errs)

    # Label aside without text
    bad_data = _valid_n64_payload()
    bad_data["asides"][1]["text"] = None
    _, errs = validate_director_plan(bad_data, ctx)
    assert any("label aside requires text" in e for e in errs)


# ===========================================================================
# 9. Degradation when Director fails 3 attempts
# ===========================================================================


def test_plan_director_degradation() -> None:
    """When director fails all 3 attempts, returns None without crashing."""
    bible = _make_test_bible()
    beats = _make_beats(64)
    # Backend returning malformed JSON on all attempts
    stub_backend = StubLLMBackend(
        [{"invalid": "payload"}, {"invalid": "payload"}, {"invalid": "payload"}]
    )

    plan, attempts = plan_director(beats, bible, stub_backend)
    assert plan is None
    assert len(attempts) == 3
    assert stub_backend.calls == 3


# ===========================================================================
# 10. License check & dropped items
# ===========================================================================


def test_license_check_verdicts_and_call_count() -> None:
    """License check drops non-ok verdicts into license_dropped; failed call fails closed."""
    beats = _make_beats(64)
    plan_dict = _valid_n64_payload()
    initial_plan = DirectorPlan.model_validate(plan_dict)

    # 5 metaphors + 6 asides = 11 license calls total
    # Metaphors: ok, adds_event, ok, contradicts, ok  (2 dropped)
    # Asides: ok, adds_dialogue, ok, adds_fact, ok, ok (2 dropped)
    responses = [
        {"verdict": "ok"},
        {"verdict": "adds_event"},
        {"verdict": "ok"},
        {"verdict": "contradicts"},
        {"verdict": "ok"},
        {"verdict": "ok"},
        {"verdict": "adds_dialogue"},
        {"verdict": "ok"},
        {"verdict": "adds_fact"},
        {"verdict": "ok"},
        {"verdict": "ok"},
    ]
    stub = StubLLMBackend(responses)

    checked_plan, dropped = run_license_checks(initial_plan, beats, stub)

    assert stub.calls == 11
    assert len(checked_plan.metaphors) == 3
    assert len(checked_plan.asides) == 4
    assert len(checked_plan.license_dropped) == 4

    verdicts = [d.verdict for d in checked_plan.license_dropped]
    assert "adds_event" in verdicts
    assert "contradicts" in verdicts
    assert "adds_dialogue" in verdicts
    assert "adds_fact" in verdicts


def test_license_check_fail_closed_on_error() -> None:
    """When a license call fails with an exception, the item is dropped (fail closed)."""
    beats = _make_beats(64)
    metaphor = MetaphorDirective(beat_i=10, image="a clock on a shelf", label="Passing")
    stub_fail = StubLLMBackend([], fail_calls=True)

    verdict = check_metaphor_license(metaphor, beats, stub_fail)
    assert verdict == "failed"


# ===========================================================================
# 11. Preview and Storyboard Markdown
# ===========================================================================


def test_storyboard_markdown_with_director(tmp_path: Path) -> None:
    """Preview storyboard.md lists creative director plan at top."""
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    director_json = job_dir / "director.json"
    plan_data = _valid_n64_payload()
    director_json.write_text(
        DirectorPlan.model_validate(plan_data).model_dump_json(indent=2), encoding="utf-8"
    )

    timeline = Timeline(
        schema_version=1,
        fps=30,
        width=1080,
        height=1920,
        duration_frames=300,
        plan_sha256="abc",
        audio=TimelineAudio(narration=TimelineNarration(src="audio/narration.wav")),
        scenes=[],
    )
    beats = _make_beats(64)
    voice = VoiceDecision(schema_version=1, voice="am_michael", source="flag", reason="flag")

    out_path = generate_storyboard_markdown(job_dir, timeline, beats, voice, {})
    content = out_path.read_text(encoding="utf-8")

    assert "## Creative Director Plan" in content
    assert "### Motifs" in content
    assert "the checkout card" in content
    assert "### Metaphors" in content
    assert "an antique brass hourglass" in content
    assert "### Asides" in content
    assert "thought (cast: c2, icon: Coins)" in content


# ===========================================================================
# 12. Director Stage Runner & Preview Revalidation
# ===========================================================================


def test_stage_director_literal_skipped(tmp_path: Path) -> None:
    """In literal mode, director stage is skipped and writes nothing."""
    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.director import run_director_stage

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "ingest.json").write_text('{"style": "literal"}', encoding="utf-8")
    (job_dir / "state.json").write_text('{"state": "segmented"}', encoding="utf-8")

    job = Job(job_dir)
    ctx = RunContext()
    run_director_stage(job, ctx)

    assert not (job_dir / "director.json").exists()
    log_content = (job_dir / "logs" / "director.log").read_text(encoding="utf-8")
    assert "skipped for literal style" in log_content
    assert "llm_calls=0 cache_hits=0" in log_content


def test_stage_director_creative_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In creative mode, director plans and checks license, creating director.json."""
    from animated_infographics.contracts.models import Beats
    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.director import run_director_stage

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "ingest.json").write_text('{"style": "creative"}', encoding="utf-8")
    (job_dir / "state.json").write_text('{"state": "segmented"}', encoding="utf-8")

    bible = _make_test_bible()
    beats = _make_beats(64)
    (job_dir / "bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "beats.json").write_text(
        Beats(schema_version=1, beats=beats).model_dump_json(indent=2), encoding="utf-8"
    )

    payload = _valid_n64_payload()
    # 1 director call + 11 license calls (all ok)
    responses = [payload] + [{"verdict": "ok"}] * 11
    stub_backend = StubLLMBackend(responses)

    # Monkeypatch OllamaBackend to return our stub
    monkeypatch.setattr(
        "animated_infographics.stages.director.OllamaBackend", lambda **kwargs: stub_backend
    )

    job = Job(job_dir)
    ctx = RunContext(style="creative")
    run_director_stage(job, ctx)

    assert (job_dir / "director.json").is_file()
    saved = DirectorPlan.model_validate_json(
        (job_dir / "director.json").read_text(encoding="utf-8")
    )
    assert len(saved.motifs) == 1
    assert len(saved.metaphors) == 5
    assert len(saved.asides) == 6

    log_content = (job_dir / "logs" / "director.log").read_text(encoding="utf-8")
    assert "Director: planned 1 motifs, 5 metaphors, 6 asides (0 license dropped)" in log_content
    assert "llm_calls=12" in log_content


def test_stage_director_degradation_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When director fails every attempt, job degrades to literal without crashing."""
    from animated_infographics.contracts.models import Beats
    from animated_infographics.jobs import Job, RunContext
    from animated_infographics.stages.director import run_director_stage

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "ingest.json").write_text('{"style": "creative"}', encoding="utf-8")
    (job_dir / "state.json").write_text('{"state": "segmented"}', encoding="utf-8")

    bible = _make_test_bible()
    beats = _make_beats(64)
    (job_dir / "bible.json").write_text(bible.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "beats.json").write_text(
        Beats(schema_version=1, beats=beats).model_dump_json(indent=2), encoding="utf-8"
    )

    # 3 failing responses
    stub_backend = StubLLMBackend([{"bad": "data"}, {"bad": "data"}, {"bad": "data"}])
    monkeypatch.setattr(
        "animated_infographics.stages.director.OllamaBackend", lambda **kwargs: stub_backend
    )

    job = Job(job_dir)
    ctx = RunContext(style="creative")
    run_director_stage(job, ctx)

    assert not (job_dir / "director.json").exists()
    assert (job_dir / ".director_degraded").is_file()

    log_content = (job_dir / "logs" / "director.log").read_text(encoding="utf-8")
    assert "degraded to literal" in log_content
