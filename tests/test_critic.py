"""Tests for people-scene critic (Issue 5 / Option A)."""

from typing import Any

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    DialogueScene,
    EmotionBeatScene,
    KineticQuoteScene,
    StatCalloutScene,
    TextThreadScene,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.contracts.templates import (
    DialogueLine,
    DialogueProps,
    EmotionBeatProps,
    KineticQuoteProps,
    StatCalloutProps,
    TextMessage,
    TextThreadProps,
)
from animated_infographics.planner.critic import (
    critic_mismatches,
    format_disagreement_message,
    needs_critic,
    validate_critic_answer,
)
from animated_infographics.planner.props import plan_storyboard


class StubLLMBackend:
    """Stub backend that simulates responses for select, props, and critic stages."""

    def __init__(self, responses_by_stage: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = {k: list(v) for k, v in responses_by_stage.items()}
        self.calls: int = 0
        self.cache_hits: int = 0
        self.call_history: list[dict[str, Any]] = []

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
        num_predict: int | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        self.calls += 1
        self.call_history.append(
            {
                "stage": stage,
                "attempt": attempt,
                "num_predict": num_predict,
                "temperature": temperature,
                "messages": messages,
                "user": user,
            }
        )
        stage_resps = self.responses.get(stage, [])
        if stage_resps:
            return stage_resps.pop(0)
        return {}


def _make_critic_test_bible() -> Bible:
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
        title="Recipe Box",
        logline="Grandma's recipe box.",
        genre="personal_story",
        cast=[
            CastMember(
                id="c1",
                name="Me",
                role="narrator",
                is_narrator=True,
                color_slot=1,
                avatar=avatar,
            ),
            CastMember(
                id="c2",
                name="Danny",
                role="brother",
                is_narrator=False,
                color_slot=2,
                avatar=avatar,
            ),
            CastMember(
                id="c3",
                name="Walt",
                role="friend",
                is_narrator=False,
                color_slot=3,
                avatar=avatar,
            ),
            CastMember(
                id="c4",
                name="Deb",
                role="mom",
                is_narrator=False,
                color_slot=4,
                avatar=avatar,
            ),
        ],
    )


def test_red_first_s012_wave_a_props_critic_disagreement() -> None:
    """Wave A s012: Danny's text attributed to c1 (narrator).

    With a stub critic answering c2 (Danny), the current planner path
    without critic accepts the scene with attribution c1 and no critic report.
    Once critic is implemented, it flags mismatch and triggers a props retry.
    """
    bible = _make_critic_test_bible()
    beat = Beat(
        i=12,
        word_start=0,
        word_end=13,
        start_ms=60800,
        end_ms=65800,
        text='"Who is Walter Lindqvist and why did he write to Grandma 60 times?"',
    )
    tokens = beat.text.split()
    words = [
        TranscriptWord(i=i, sentence_i=0, text=tok, start_ms=i * 300, end_ms=(i + 1) * 300)
        for i, tok in enumerate(tokens)
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=70000,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text=beat.text,
                start_ms=0,
                end_ms=len(tokens) * 300,
                word_start=0,
                word_end=len(tokens),
                paragraph_i=0,
                is_title=False,
            )
        ],
    )

    # 1. Props returns s012 with attribution_cast_id "c1"
    initial_props = {
        "text": "Who is Walter Lindqvist and why did he write to Grandma 60 times?",
        "emphasis": [],
        "attribution_cast_id": "c1",
    }
    # 2. Critic answers "c2" (Danny)
    critic_answer = {"speaker": "c2"}
    # 3. Props retry responds with corrected props "c2"
    corrected_props = {
        "text": "Who is Walter Lindqvist and why did he write to Grandma 60 times?",
        "emphasis": [],
        "attribution_cast_id": "c2",
    }

    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "kinetic_quote", "alternate": "dialogue"}]}
            ],
            "props": [initial_props, corrected_props],
            "critic": [critic_answer],
        }
    )

    title_beat = Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=1000, text="Title")
    storyboard, report = plan_storyboard(transcript, [title_beat, beat], bible, backend)

    assert len(storyboard.scenes) == 2
    scene = storyboard.scenes[1]
    rep_scene = report.scenes[1]

    assert hasattr(rep_scene, "critic"), "PlanReportScene must have critic attribute"
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.mismatches == ["attribution_cast_id: c1 vs c2"]
    assert rep_scene.critic.changed is True
    assert scene.props.attribution_cast_id == "c2"


def test_needs_critic() -> None:
    """Verify which scene types require the blind critic per §11."""
    d_scene = DialogueScene(
        id="s001",
        beat_i=1,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Hello", tone="neutral")]),
    )
    assert needs_critic(d_scene) is True

    tt_scene = TextThreadScene(
        id="s002",
        beat_i=2,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Danny",
            messages=[
                TextMessage(from_="me", text="Hey"),
                TextMessage(from_="them", text="What's up?"),
            ],
        ),
    )
    assert needs_critic(tt_scene) is True

    eb_scene = EmotionBeatScene(
        id="s003",
        beat_i=3,
        template="emotion_beat",
        props=EmotionBeatProps(cast_id="c1", emotion="happy"),
    )
    assert needs_critic(eb_scene) is True

    kq_attributed = KineticQuoteScene(
        id="s004",
        beat_i=4,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Quote", emphasis=[], attribution_cast_id="c1"),
    )
    assert needs_critic(kq_attributed) is True

    kq_unattributed = KineticQuoteScene(
        id="s005",
        beat_i=5,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Quote", emphasis=[], attribution_cast_id=None),
    )
    assert needs_critic(kq_unattributed) is False

    fallback_scene = DialogueScene(
        id="s006",
        beat_i=6,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Hello", tone="neutral")]),
        rationale="deterministic fallback",
    )
    assert needs_critic(fallback_scene) is False

    stat_scene = StatCalloutScene(
        id="s007",
        beat_i=7,
        template="stat_callout",
        props=StatCalloutProps(value=42.0, decimals=0, caption="Meaning of life"),
    )
    assert needs_critic(stat_scene) is False


def test_critic_mismatch_rules_unit() -> None:
    """Test every rule row in design_planner.md §11 and design_testing_and_validation.md §2."""
    bible = _make_critic_test_bible()

    # 1. unknown speaker -> agree (never a mismatch for who)
    kq_c3 = KineticQuoteScene(
        id="s001",
        beat_i=1,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Test", emphasis=[], attribution_cast_id="c3"),
    )
    assert critic_mismatches(kq_c3, {"speaker": "unknown"}, bible) == []

    # 2. unknown tone + angry -> mismatch
    diag_angry = DialogueScene(
        id="s002",
        beat_i=2,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Rose?", tone="angry")]),
    )
    crit_angry = {"lines": [{"speaker": "c1", "tone": "unknown"}]}
    mismatches_angry = critic_mismatches(diag_angry, crit_angry, bible)
    assert mismatches_angry == ["lines[0].tone: angry vs unknown"]

    # 3. unknown tone + neutral -> agree
    diag_neutral = DialogueScene(
        id="s003",
        beat_i=3,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Rose?", tone="neutral")]),
    )
    crit_neutral = {"lines": [{"speaker": "c1", "tone": "unknown"}]}
    assert critic_mismatches(diag_neutral, crit_neutral, bible) == []

    # 4. narration + narrator id (c1) -> agree
    kq_narrator = KineticQuoteScene(
        id="s004",
        beat_i=4,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Test", emphasis=[], attribution_cast_id="c1"),
    )
    assert critic_mismatches(kq_narrator, {"speaker": "narration"}, bible) == []

    # 5. narration + another id (c2) -> mismatch
    kq_non_narrator = KineticQuoteScene(
        id="s005",
        beat_i=5,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Test", emphasis=[], attribution_cast_id="c2"),
    )
    mismatches_narration = critic_mismatches(kq_non_narrator, {"speaker": "narration"}, bible)
    assert mismatches_narration == ["attribution_cast_id: c2 vs narration"]

    # 6. emotion unknown -> agree
    eb_scene = EmotionBeatScene(
        id="s006",
        beat_i=6,
        template="emotion_beat",
        props=EmotionBeatProps(cast_id="c1", emotion="happy"),
    )
    assert critic_mismatches(eb_scene, {"cast_id": "c1", "emotion": "unknown"}, bible) == []

    # 7. emotion mismatch -> mismatch
    mismatches_eb = critic_mismatches(eb_scene, {"cast_id": "c1", "emotion": "sad"}, bible)
    assert mismatches_eb == ["emotion: happy vs sad"]


def test_critic_call_limits_on_mismatch() -> None:
    """Verify on mismatch exactly one props retry and zero further critic calls."""
    bible = _make_critic_test_bible()
    beat = Beat(i=1, word_start=0, word_end=5, start_ms=0, end_ms=3000, text="Hello there")
    tokens = beat.text.split()
    words = [
        TranscriptWord(i=i, sentence_i=0, text=tok, start_ms=i * 300, end_ms=(i + 1) * 300)
        for i, tok in enumerate(tokens)
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=5000,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text=beat.text,
                start_ms=0,
                end_ms=len(tokens) * 300,
                word_start=0,
                word_end=len(tokens),
                paragraph_i=0,
                is_title=False,
            )
        ],
    )

    initial_props = {"lines": [{"cast_id": "c1", "text": "Hello there", "tone": "angry"}]}
    critic_answer = {"lines": [{"speaker": "c1", "tone": "unknown"}]}
    corrected_props = {"lines": [{"cast_id": "c1", "text": "Hello there", "tone": "neutral"}]}

    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "dialogue", "alternate": "kinetic_quote"}]}
            ],
            "props": [initial_props, corrected_props],
            "critic": [critic_answer],
        }
    )

    title_beat = Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=1000, text="Title")
    storyboard, report = plan_storyboard(transcript, [title_beat, beat], bible, backend)

    # Check stage calls in history
    critic_calls = [h for h in backend.call_history if h["stage"] == "critic"]
    props_calls = [h for h in backend.call_history if h["stage"] == "props"]

    assert len(critic_calls) == 1, "Must make exactly 1 critic call (no second call)"
    assert len(props_calls) == 2, "Must make initial props + exactly 1 props retry"

    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.changed is True


def test_critic_unavailable_when_all_attempts_fail() -> None:
    """Verify critic that fails 3 times results in scene accepted and status 'unavailable'."""
    bible = _make_critic_test_bible()
    beat = Beat(i=1, word_start=0, word_end=5, start_ms=0, end_ms=3000, text="Hello there")
    tokens = beat.text.split()
    words = [
        TranscriptWord(i=i, sentence_i=0, text=tok, start_ms=i * 300, end_ms=(i + 1) * 300)
        for i, tok in enumerate(tokens)
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=5000,
        words=words,
        sentences=[
            TranscriptSentence(
                i=0,
                text=beat.text,
                start_ms=0,
                end_ms=len(tokens) * 300,
                word_start=0,
                word_end=len(tokens),
                paragraph_i=0,
                is_title=False,
            )
        ],
    )

    initial_props = {"lines": [{"cast_id": "c1", "text": "Hello there", "tone": "angry"}]}

    # Critic provides 3 invalid responses (e.g. wrong type or empty)
    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "dialogue", "alternate": "kinetic_quote"}]}
            ],
            "props": [initial_props],
            "critic": [{}, {}, {}],
        }
    )

    title_beat = Beat(i=0, word_start=0, word_end=1, start_ms=0, end_ms=1000, text="Title")
    storyboard, report = plan_storyboard(transcript, [title_beat, beat], bible, backend)

    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "unavailable"
    assert rep_scene.critic.mismatches == []
    assert rep_scene.critic.changed is False


def test_validate_critic_answer_length_mismatch() -> None:
    """Verify wrong-length lines/messages in critic answer returns error."""
    diag = DialogueScene(
        id="s001",
        beat_i=1,
        template="dialogue",
        props=DialogueProps(
            lines=[
                DialogueLine(cast_id="c1", text="Line 1", tone="neutral"),
                DialogueLine(cast_id="c2", text="Line 2", tone="neutral"),
            ]
        ),
    )
    # Critic gives only 1 line
    ans, errors = validate_critic_answer(diag, {"lines": [{"speaker": "c1", "tone": "neutral"}]})
    assert len(errors) == 1
    assert "critic lines length mismatch: expected 2, got 1" in errors[0]

    # Matching length gives 0 errors
    ans_good, errors_good = validate_critic_answer(
        diag,
        {
            "lines": [
                {"speaker": "c1", "tone": "neutral"},
                {"speaker": "c2", "tone": "neutral"},
            ]
        },
    )
    assert errors_good == []


def test_critic_regression_cases_classification() -> None:
    """Verify all 4 regression cases from design_planner.md §11 table."""
    bible = _make_critic_test_bible()

    # Case A: Danny's text "Who is Walter Lindqvist…" as kinetic_quote
    # Props: attribution c1, Critic: c2 -> Expected: mismatch
    kq_a = KineticQuoteScene(
        id="s012",
        beat_i=12,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="Who is Walter Lindqvist and why did he write to Grandma 60 times?",
            emphasis=[],
            attribution_cast_id="c1",
        ),
    )
    assert critic_mismatches(kq_a, {"speaker": "c2"}, bible) == ["attribution_cast_id: c1 vs c2"]

    # Case B: "Rose?" as dialogue line
    # Props: c1, tone angry, Critic: c1, unknown -> Expected: mismatch (tone)
    d_b = DialogueScene(
        id="s015",
        beat_i=15,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Rose?", tone="angry")]),
    )
    assert critic_mismatches(d_b, {"lines": [{"speaker": "c1", "tone": "unknown"}]}, bible) == [
        "lines[0].tone: angry vs unknown"
    ]

    # Case B': the same line with tone neutral
    # Props: c1, neutral, Critic: c1, unknown -> Expected: agree
    d_b_prime = DialogueScene(
        id="s015",
        beat_i=15,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Rose?", tone="neutral")]),
    )
    crit_b_prime = {"lines": [{"speaker": "c1", "tone": "unknown"}]}
    assert critic_mismatches(d_b_prime, crit_b_prime, bible) == []

    # Case C: "I've been waiting for someone to call about the pie."
    # Props: attribution c3, Critic: unknown -> Expected: agree
    kq_c = KineticQuoteScene(
        id="s016",
        beat_i=16,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="I've been waiting for someone to call about the pie.",
            emphasis=[],
            attribution_cast_id="c3",
        ),
    )
    assert critic_mismatches(kq_c, {"speaker": "unknown"}, bible) == []


def test_falsify_tone_rule_and_who_rule() -> None:
    """Falsification tests per agent_execution_guide.md:

    1. Make tone rule ignore unknown tone -> Case B is accepted (agree) -> red.
    2. Make unknown who count as mismatch -> Case C is flagged -> red.
    """
    bible = _make_critic_test_bible()

    # Case B scene: angry tone vs unknown critic tone
    d_b = DialogueScene(
        id="s015",
        beat_i=15,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Rose?", tone="angry")]),
    )
    critic_b = {"lines": [{"speaker": "c1", "tone": "unknown"}]}

    # Flawed tone rule that ignores "unknown" tone
    flawed_tone_mismatches = []
    line = d_b.props.lines[0]
    crit_tone = critic_b["lines"][0]["tone"]
    if crit_tone != "unknown" and crit_tone != line.tone:
        flawed_tone_mismatches.append(f"lines[0].tone: {line.tone} vs {crit_tone}")
    assert flawed_tone_mismatches == [], "Flawed tone rule erroneously agrees on Case B"

    # Real rule MUST mismatch on Case B
    real_b_mismatches = critic_mismatches(d_b, critic_b, bible)
    assert real_b_mismatches == ["lines[0].tone: angry vs unknown"], "Real rule must flag Case B"

    # Case C scene: attribution c3 vs unknown critic speaker
    kq_c = KineticQuoteScene(
        id="s016",
        beat_i=16,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="I've been waiting for someone to call about the pie.",
            emphasis=[],
            attribution_cast_id="c3",
        ),
    )
    critic_c = {"speaker": "unknown"}

    # Flawed who rule that treats "unknown" as a mismatch
    flawed_who_mismatches = []
    props_speaker = kq_c.props.attribution_cast_id
    crit_speaker = critic_c["speaker"]
    if crit_speaker != props_speaker:
        flawed_who_mismatches.append(f"attribution_cast_id: {props_speaker} vs {crit_speaker}")
    assert flawed_who_mismatches == ["attribution_cast_id: c3 vs unknown"], (
        "Flawed who rule erroneously flags Case C"
    )

    # Real rule MUST agree on Case C
    real_c_mismatches = critic_mismatches(kq_c, critic_c, bible)
    assert real_c_mismatches == [], "Real rule must NOT flag Case C"


def test_format_disagreement_message() -> None:
    """Verify disagreement message matches verbatim specification."""
    mismatches = ["lines[0].tone: angry vs unknown", "attribution_cast_id: c1 vs c2"]
    msg = format_disagreement_message(mismatches)
    expected = (
        "A second, independent reading of this beat disagrees:\n"
        "- lines[0].tone: you said angry; the reading says unknown\n"
        "- attribution_cast_id: you said c1; the reading says c2\n"
        "Fix the props if that reading fits the beat text better; otherwise keep yours."
    )
    assert msg == expected
