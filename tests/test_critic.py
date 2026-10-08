"""Tests for people-scene critic (Issue 5 / Option A)."""

import json
from pathlib import Path
from typing import Any

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
    DialogueScene,
    EmotionBeatScene,
    KineticQuoteScene,
    Scene,
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
    build_critic_request,
    critic_mismatches,
    enforce_reading,
    format_disagreement_message,
    needs_critic,
    resolve_contact,
    validate_critic_answer,
)
from animated_infographics.planner.props import (
    _evaluate_scene_critic,
    plan_single_template_props,
    plan_storyboard,
)


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
    beat_text = '"Who is Walter Lindqvist and why did he write 60 times?"'
    tokens = ["Danny"] + beat_text.split()
    words = [
        TranscriptWord(i=i, sentence_i=0, text=tok, start_ms=i * 300, end_ms=(i + 1) * 300)
        for i, tok in enumerate(tokens)
    ]
    beat = Beat(
        i=12,
        word_start=1,
        word_end=len(tokens),
        start_ms=60800,
        end_ms=65800,
        text=beat_text,
    )
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
        "text": "Who is Walter Lindqvist and why did he write 60 times?",
        "emphasis": [],
        "attribution_cast_id": "c1",
    }
    # 2. Critic answers "c2" (Danny)
    critic_answer = {"speaker": "c2"}
    # 3. Props retry responds with corrected props "c2"
    corrected_props = {
        "text": "Who is Walter Lindqvist and why did he write 60 times?",
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
        props=StatCalloutProps(value=42.0, decimals=0),
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

    # 6. emotion unknown + non-neutral -> mismatch
    eb_scene = EmotionBeatScene(
        id="s006",
        beat_i=6,
        template="emotion_beat",
        props=EmotionBeatProps(cast_id="c1", emotion="happy"),
    )
    assert critic_mismatches(eb_scene, {"cast_id": "c1", "emotion": "unknown"}, bible) == [
        "emotion: happy vs unknown"
    ]

    # 6b. emotion unknown + neutral -> agree
    eb_neutral = EmotionBeatScene(
        id="s007",
        beat_i=6,
        template="emotion_beat",
        props=EmotionBeatProps(cast_id="c1", emotion="neutral"),
    )
    assert critic_mismatches(eb_neutral, {"cast_id": "c1", "emotion": "unknown"}, bible) == []

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

    # Case E: Quote with speaker named in sentence before (Danny found letters)
    # Props: attribution c1, Critic: c3 -> Expected: mismatch
    kq_e = KineticQuoteScene(
        id="s012",
        beat_i=12,
        template="kinetic_quote",
        props=KineticQuoteProps(
            text="Who is Walter Lindqvist and why did he write to Grandma 60 times?",
            emphasis=[],
            attribution_cast_id="c1",
        ),
    )
    assert critic_mismatches(kq_e, {"speaker": "c3"}, bible) == ["attribution_cast_id: c1 vs c3"]

    # Case H: Text thread with consecutive "them" messages
    # Props: senders them x3, Critic keyed normalized -> Expected: agree
    tt_h = TextThreadScene(
        id="s011",
        beat_i=11,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Danny",
            contact_cast_id=None,
            messages=[
                TextMessage(
                    from_="them",
                    text="Found this in the attic while clearing out the house.",
                ),
                TextMessage(from_="them", text="A whole shoebox of letters."),
                TextMessage(from_="them", text="[Photo Attached]"),
            ],
        ),
    )
    norm_h, errs_h = validate_critic_answer(
        tt_h,
        {
            "message_1": "them",
            "message_2": "them",
            "message_3": "them",
            "contact": "c2",
        },
    )
    assert errs_h == []
    assert critic_mismatches(tt_h, norm_h, bible) == []

    # Case F: Text thread with wrong contact name (Sofia instead of Deb)
    # Props: contact_name "Sofia", Critic: "c4" (Deb) -> Expected: mismatch
    tt_f = TextThreadScene(
        id="s018",
        beat_i=18,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Sofia",
            contact_cast_id=None,
            messages=[
                TextMessage(from_="them", text="Keep the room."),
                TextMessage(from_="them", text="He's never missed one."),
            ],
        ),
    )
    norm_f, errs_f = validate_critic_answer(
        tt_f,
        {
            "message_1": "them",
            "message_2": "them",
            "contact": "c4",
        },
    )
    assert errs_f == []
    assert critic_mismatches(tt_f, norm_f, bible) == ["contact: Sofia vs Deb (c4)"]

    # Case G: Text thread with non-cast contact (Wife)
    # Props: contact_name "Wife", Critic: "unknown" -> Expected: agree
    tt_g = TextThreadScene(
        id="s004",
        beat_i=4,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Wife",
            contact_cast_id=None,
            messages=[
                TextMessage(from_="me", text="You still awake?"),
                TextMessage(from_="them", text="Yeah, just reading. Why?"),
                TextMessage(from_="me", text="Just checking in. Love you."),
            ],
        ),
    )
    norm_g, errs_g = validate_critic_answer(
        tt_g,
        {
            "message_1": "me",
            "message_2": "them",
            "message_3": "me",
            "contact": "unknown",
        },
    )
    assert errs_g == []
    assert critic_mismatches(tt_g, norm_g, bible) == []


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


def test_critic_passage_framing_no_context_only() -> None:
    """Verify build_critic_request uses exact passage framing header and no 'context only'."""
    bible = _make_critic_test_bible()
    kq = KineticQuoteScene(
        id="s012",
        beat_i=12,
        template="kinetic_quote",
        props=KineticQuoteProps(text="A quote", emphasis=[], attribution_cast_id="c1"),
    )
    b0 = Beat(i=10, text="Beat before previous.", start_ms=0, end_ms=1000, word_start=0, word_end=3)
    b1 = Beat(i=11, text="Previous beat.", start_ms=1000, end_ms=2000, word_start=3, word_end=5)
    b2 = Beat(i=12, text="Current beat.", start_ms=2000, end_ms=3000, word_start=5, word_end=7)
    b3 = Beat(i=13, text="Next beat.", start_ms=3000, end_ms=4000, word_start=7, word_end=9)

    system, user, _ = build_critic_request(kq, b2, b1, b3, bible, before_prev_beat=b0)

    expected_header = (
        "Passage (read all of it; who speaks is often named in the sentence before a quote):"
    )
    assert expected_header in user, "Must include verbatim passage header"
    assert "context only" not in user.lower(), (
        "Must NOT include 'context only' anywhere in user prompt"
    )
    assert "context only" not in system.lower(), "Must NOT include 'context only' in system prompt"
    assert "Beat before previous. Previous beat. Current beat. Next beat." in user


def test_text_thread_critic_schema_keyed() -> None:
    """Verify text_thread critic schema has keyed messages, then contact, all required."""
    bible = _make_critic_test_bible()
    tt = TextThreadScene(
        id="s011",
        beat_i=11,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Danny",
            contact_cast_id=None,
            messages=[
                TextMessage(from_="them", text="msg1"),
                TextMessage(from_="them", text="msg2"),
                TextMessage(from_="them", text="msg3"),
            ],
        ),
    )
    beat = Beat(i=11, text="Texting", start_ms=0, end_ms=1000, word_start=0, word_end=1)
    _, user, schema = build_critic_request(tt, beat, None, None, bible)

    expected_q = (
        "Who is the other person in this conversation, according to the passage? "
        'Answer a cast id, or "unknown" if the passage does not say '
        "or they are not in the cast list."
    )
    assert expected_q in user, "Must include contact question verbatim"

    props = schema["properties"]
    prop_keys = list(props.keys())
    assert prop_keys == ["message_1", "message_2", "message_3", "contact"], "contact must be last"
    assert schema["required"] == ["message_1", "message_2", "message_3", "contact"]
    assert schema["additionalProperties"] is False
    for k in ["message_1", "message_2", "message_3"]:
        assert props[k]["enum"] == ["me", "them", "unknown"]
    # Cast members: c1 (narrator), c2 (Danny), c3 (Walt), c4 (Deb)
    # Non-narrators: c2, c3, c4
    assert props["contact"]["enum"] == ["c2", "c3", "c4", "unknown"]


def test_validate_critic_answer_keyed_text_thread() -> None:
    """Verify validation of keyed text_thread critic answers."""
    tt = TextThreadScene(
        id="s011",
        beat_i=11,
        template="text_thread",
        props=TextThreadProps(
            contact_name="Danny",
            contact_cast_id=None,
            messages=[
                TextMessage(from_="them", text="msg1"),
                TextMessage(from_="them", text="msg2"),
                TextMessage(from_="them", text="msg3"),
            ],
        ),
    )

    # Valid answer normalizes to {"messages": [{"sender": ...}, ...], "contact": ...}
    valid_raw = {
        "message_1": "them",
        "message_2": "me",
        "message_3": "them",
        "contact": "c2",
    }
    normalized, errors = validate_critic_answer(tt, valid_raw)
    assert errors == []
    assert normalized == {
        "messages": [
            {"sender": "them"},
            {"sender": "me"},
            {"sender": "them"},
        ],
        "contact": "c2",
    }

    # Missing message_2 is a failed attempt with specific error message
    missing_raw = {"message_1": "them", "message_3": "them", "contact": "c2"}
    _, errors_missing = validate_critic_answer(tt, missing_raw)
    assert errors_missing == ["critic messages missing: message_2"]

    # Missing contact is a failed attempt
    missing_contact_raw = {
        "message_1": "them",
        "message_2": "me",
        "message_3": "them",
    }
    _, errors_contact = validate_critic_answer(tt, missing_contact_raw)
    assert errors_contact == ["critic contact missing"]


def test_resolve_contact() -> None:
    """Verify resolve_contact behavior per design_planner.md §11."""
    bible = _make_critic_test_bible()

    sample_msgs = [
        TextMessage(from_="them", text="hi"),
        TextMessage(from_="me", text="hello"),
    ]

    # 1. props.contact_cast_id set -> returns it directly
    p_set = TextThreadProps(
        contact_name="Random Name",
        contact_cast_id="c3",
        messages=sample_msgs,
    )
    assert resolve_contact(p_set, bible) == "c3"

    # 2. props.contact_cast_id is None, contact_name matches non-narrator (with case/whitespace)
    p_match = TextThreadProps(
        contact_name="  danny  ",
        contact_cast_id=None,
        messages=sample_msgs,
    )
    assert resolve_contact(p_match, bible) == "c2"

    # 3. contact_name matches narrator -> returns None (narrator excluded)
    p_narrator = TextThreadProps(
        contact_name="Me",
        contact_cast_id=None,
        messages=sample_msgs,
    )
    assert resolve_contact(p_narrator, bible) is None

    # 4. contact_name does not match any cast member -> returns None
    p_unknown = TextThreadProps(
        contact_name="Stranger",
        contact_cast_id=None,
        messages=sample_msgs,
    )
    assert resolve_contact(p_unknown, bible) is None


def test_text_thread_contact_fill_in_props_planning() -> None:
    """Verify props planning fills contact_cast_id when matching cast name is present."""
    bible = _make_critic_test_bible()
    beat = Beat(i=1, text="Texting Danny", start_ms=0, end_ms=1000, word_start=0, word_end=2)
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=1000,
        words=[],
        sentences=[],
    )

    # Backend provides contact_cast_id as None, but contact_name "Danny"
    stub_raw = {
        "contact_name": "Danny",
        "contact_cast_id": None,
        "messages": [
            {"from": "them", "text": "Are you there?"},
            {"from": "me", "text": "Yes I am."},
        ],
    }
    backend = StubLLMBackend({"props": [stub_raw]})

    scene, errors, attempts = plan_single_template_props(
        template_name="text_thread",
        scene_id="s001",
        beat_i=1,
        beat=beat,
        prev_beat=None,
        next_beat=None,
        transcript=transcript,
        bible=bible,
        backend=backend,
        prompt_template="{this_beat_text}",
        compact_bible="Bible info",
    )

    assert errors == []
    assert scene is not None
    assert isinstance(scene, TextThreadScene)
    # Must be filled to "c2" (Danny)
    assert scene.props.contact_cast_id == "c2"


def _make_transcript_and_beats(texts: list[str]) -> tuple[Transcript, list[Beat]]:
    words: list[TranscriptWord] = []
    sentences: list[TranscriptSentence] = []
    beats: list[Beat] = []
    word_idx = 0
    for idx, text in enumerate(texts):
        toks = text.split() or ["word"]
        start_w = word_idx
        for tok in toks:
            words.append(
                TranscriptWord(
                    i=word_idx,
                    sentence_i=idx,
                    text=tok,
                    start_ms=word_idx * 300,
                    end_ms=(word_idx + 1) * 300,
                )
            )
            word_idx += 1
        end_w = word_idx
        b = Beat(
            i=idx,
            word_start=start_w,
            word_end=end_w,
            start_ms=start_w * 300,
            end_ms=end_w * 300,
            text=text,
        )
        beats.append(b)
        sentences.append(
            TranscriptSentence(
                i=idx,
                text=text,
                start_ms=b.start_ms,
                end_ms=b.end_ms,
                word_start=start_w,
                word_end=end_w,
                paragraph_i=0,
                is_title=(idx == 0),
            )
        )
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=max((b.end_ms for b in beats), default=1000),
        words=words,
        sentences=sentences,
    )
    return transcript, beats


def test_critic_retry_recovers_on_attempt_2_or_3() -> None:
    """Verify critic retry allows 3 attempts and recovers on attempt 2 (C3)."""
    bible = _make_critic_test_bible()
    transcript, beats = _make_transcript_and_beats(["Title", "A quote from Danny"])
    initial_props = {"text": "A quote from Danny", "emphasis": [], "attribution_cast_id": "c1"}
    critic_answer = {"speaker": "c2"}
    # Attempt 1 of retry fails with validation error (empty dict), attempt 2 succeeds
    invalid_retry_props: dict[str, Any] = {}
    valid_retry_props = {
        "text": "A quote from Danny",
        "emphasis": [],
        "attribution_cast_id": "c2",
    }

    backend = StubLLMBackend(
        {
            "select": [
                {
                    "choices": [
                        {"beat_i": 1, "primary": "kinetic_quote", "alternate": "stat_callout"}
                    ]
                }
            ],
            "props": [initial_props, invalid_retry_props, valid_retry_props],
            "critic": [critic_answer],
        }
    )

    storyboard, report = plan_storyboard(transcript, beats, bible, backend)

    scene = storyboard.scenes[1]
    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.changed is True
    assert scene.props.attribution_cast_id == "c2"


def test_critic_tone_neutral_repair_when_retry_exhausted() -> None:
    """Verify dialogue tone is repaired to neutral when retry fails and tone was only mismatch."""
    bible = _make_critic_test_bible()
    transcript, beats = _make_transcript_and_beats(["Title", "Rose?"])
    initial_props = {"lines": [{"cast_id": "c1", "text": "Rose?", "tone": "angry"}]}
    critic_answer = {"lines": [{"speaker": "c1", "tone": "unknown"}]}
    # All 3 retry attempts return invalid props
    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "dialogue", "alternate": "stat_callout"}]}
            ],
            "props": [initial_props, {}, {}, {}],
            "critic": [critic_answer],
        }
    )

    storyboard, report = plan_storyboard(transcript, beats, bible, backend)

    scene = storyboard.scenes[1]
    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.changed is True
    assert getattr(rep_scene.critic, "repair", None) == "tone_neutral"
    assert scene.props.lines[0].tone == "neutral"


def test_critic_text_thread_mismatch_keeps_original_and_records_retry_errors() -> None:
    """Verify un-enforced mismatch keeps original scene and records retry_errors on failure."""
    bible = _make_critic_test_bible()
    transcript, beats = _make_transcript_and_beats(["Title Danny", "A text message"])
    initial_props = {
        "contact_name": "Danny",
        "contact_cast_id": "c2",
        "messages": [
            {"from_": "me", "text": "Hello"},
            {"from_": "them", "text": "Hi there"},
        ],
    }
    critic_answer = {"message_1": "them", "message_2": "them", "contact": "c2"}
    # All retry attempts fail
    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "text_thread", "alternate": "stat_callout"}]}
            ],
            "props": [initial_props, {}, {}, {}],
            "critic": [critic_answer],
        }
    )

    storyboard, report = plan_storyboard(transcript, beats, bible, backend)

    scene = storyboard.scenes[1]
    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.changed is False
    assert getattr(rep_scene.critic, "repair", None) is None
    assert len(getattr(rep_scene.critic, "retry_errors", [])) > 0
    assert scene.props.messages[0].from_ == "me"


def test_critic_identical_retry_changed_is_false() -> None:
    """Verify identical retry sets changed=False when no enforcement alters props."""
    bible = _make_critic_test_bible()
    transcript, beats = _make_transcript_and_beats(["Title Danny", "A text message"])
    initial_props = {
        "contact_name": "Danny",
        "contact_cast_id": "c2",
        "messages": [
            {"from_": "me", "text": "Hello"},
            {"from_": "them", "text": "Hi there"},
        ],
    }
    critic_answer = {"message_1": "them", "message_2": "them", "contact": "c2"}
    identical_retry_props = dict(initial_props)

    backend = StubLLMBackend(
        {
            "select": [
                {"choices": [{"beat_i": 1, "primary": "text_thread", "alternate": "stat_callout"}]}
            ],
            "props": [initial_props, identical_retry_props],
            "critic": [critic_answer],
        }
    )

    storyboard, report = plan_storyboard(transcript, beats, bible, backend)

    rep_scene = report.scenes[1]
    assert rep_scene.critic.status == "mismatch_retried"
    assert rep_scene.critic.changed is False


def test_r3_repair_calls_critic() -> None:
    """Verify scene rebuilt by rule R3 calls critic when template requires it."""
    bible = _make_critic_test_bible()
    transcript, beats = _make_transcript_and_beats(
        ["Title", "Danny arrived.", "I answered.", "Danny spoke up."]
    )
    intro1 = {"cast_id": "c2", "descriptor": "Brother"}
    d1 = {"lines": [{"cast_id": "c1", "text": "I answered him", "tone": "neutral"}]}
    intro2 = {"cast_id": "c2", "descriptor": "Brother"}
    d2 = {"lines": [{"cast_id": "c2", "text": "Hello there", "tone": "neutral"}]}
    critic_d1 = {"lines": [{"speaker": "c1", "tone": "neutral"}]}
    critic_d2 = {"lines": [{"speaker": "c2", "tone": "neutral"}]}

    backend = StubLLMBackend(
        {
            "select": [
                {
                    "choices": [
                        {"beat_i": 1, "primary": "character_intro", "alternate": "stat_callout"},
                        {"beat_i": 2, "primary": "dialogue", "alternate": "kinetic_quote"},
                        {"beat_i": 3, "primary": "character_intro", "alternate": "dialogue"},
                    ]
                }
            ],
            "props": [intro1, d1, intro2, d2],
            "critic": [critic_d1, critic_d2],
        }
    )

    storyboard, report = plan_storyboard(transcript, beats, bible, backend)

    rep_scene3 = report.scenes[3]
    assert rep_scene3.final_template == "dialogue"
    # R3 replaced intro with dialogue, which needs_critic. Must NOT be not_applicable!
    assert rep_scene3.critic.status == "agree"


def test_critic_enforcement_frozen_cases() -> None:
    """Verify critic enforcement on 7 frozen cases from critic_enforcement_cases.json per E1."""
    cases_path = Path(__file__).resolve().parent / "data" / "critic_enforcement_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)

    transcript = Transcript(
        schema_version=1, source="tts", audio_path="", duration_ms=10000, sentences=[], words=[]
    )

    for case_data in data["cases"]:
        case_id = case_data["case"]
        bible = Bible.model_validate(case_data["bible"])
        template = case_data["template"]
        props_dict = case_data["scene"]["props"]
        beats_dict = case_data["beats"]
        reading = case_data["critic_readings_seeds_7_8_9"][0]

        if template == "dialogue":
            scene: Scene = DialogueScene(
                id=case_data["scene"]["id"],
                beat_i=case_data["scene"]["beat_i"],
                template="dialogue",
                props=DialogueProps.model_validate(props_dict),
            )
        elif template == "kinetic_quote":
            scene = KineticQuoteScene(
                id=case_data["scene"]["id"],
                beat_i=case_data["scene"]["beat_i"],
                template="kinetic_quote",
                props=KineticQuoteProps.model_validate(props_dict),
            )
        elif template == "emotion_beat":
            scene = EmotionBeatScene(
                id=case_data["scene"]["id"],
                beat_i=case_data["scene"]["beat_i"],
                template="emotion_beat",
                props=EmotionBeatProps.model_validate(props_dict),
            )
        else:
            raise ValueError(f"Unexpected template {template}")

        # The stub backend returns recorded reading on critic call, and SAME props on retry
        backend = StubLLMBackend({"critic": [reading], "props": [props_dict]})
        b_bp = Beat(
            i=0,
            text=beats_dict["before_previous"],
            start_ms=0,
            end_ms=1000,
            word_start=0,
            word_end=10,
        )
        b_p = Beat(
            i=1, text=beats_dict["previous"], start_ms=1000, end_ms=2000, word_start=10, word_end=20
        )
        b_curr = Beat(
            i=2, text=beats_dict["current"], start_ms=2000, end_ms=3000, word_start=20, word_end=30
        )
        b_n = Beat(
            i=3, text=beats_dict["next"], start_ms=3000, end_ms=4000, word_start=30, word_end=40
        )

        final_scene, rep, _ = _evaluate_scene_critic(
            scene, b_curr, b_p, b_n, transcript, bible, backend, "", "", before_prev_beat=b_bp
        )

        assert rep.status == "mismatch_retried"
        assert rep.changed is True

        if case_id == "story-recipe-box:s025":
            assert rep.repair == "tone_neutral"
            assert isinstance(final_scene, DialogueScene)
            assert [line.tone for line in final_scene.props.lines] == ["neutral", "neutral"]
        elif case_id == "story-recipe-box:s007":
            assert rep.repair == "tone_neutral"
            assert isinstance(final_scene, DialogueScene)
            assert final_scene.props.lines[0].tone == "neutral"
            assert final_scene.props.lines[1].tone == "neutral"
        elif case_id == "story-recipe-box:s013":
            assert rep.repair == "tone_neutral"
            assert isinstance(final_scene, DialogueScene)
            assert final_scene.props.lines[0].tone == "neutral"
        elif case_id in ("emu-war:s010", "story-room-12:s022"):
            assert rep.repair == "attribution_dropped"
            assert isinstance(final_scene, KineticQuoteScene)
            assert final_scene.props.attribution_cast_id is None
        elif case_id in ("emu-war:s018", "story-recipe-box:s012"):
            assert rep.repair == "emotion_neutral"
            assert isinstance(final_scene, EmotionBeatScene)
            assert final_scene.props.emotion == "neutral"

    # Additional assertions required by E1:
    b_test = _make_critic_test_bible()

    # 1. A tone the reading confirms survives
    d_scene = DialogueScene(
        id="s001",
        beat_i=1,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Yes!", tone="happy")]),
    )
    res_confirmed, rep_name = enforce_reading(
        d_scene, {"lines": [{"speaker": "c1", "tone": "happy"}]}, b_test
    )
    assert rep_name is None
    assert isinstance(res_confirmed, DialogueScene)
    assert res_confirmed.props.lines[0].tone == "happy"

    # 2. An unknown quote reading removes nothing
    kq_scene = KineticQuoteScene(
        id="s002",
        beat_i=2,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Quote", emphasis=[], attribution_cast_id="c2"),
    )
    res_kq, rep_kq = enforce_reading(kq_scene, {"speaker": "unknown"}, b_test)
    assert rep_kq is None
    assert isinstance(res_kq, KineticQuoteScene)
    assert res_kq.props.attribution_cast_id == "c2"

    # 3. A retry that fixes the scene needs no enforcement (repair: null)
    kq_init = KineticQuoteScene(
        id="s003",
        beat_i=3,
        template="kinetic_quote",
        props=KineticQuoteProps(text="Quote", emphasis=[], attribution_cast_id="c2"),
    )
    backend_fixed = StubLLMBackend(
        {
            "critic": [{"speaker": "c3"}],
            "props": [{"text": "Quote", "emphasis": [], "attribution_cast_id": "c3"}],
        }
    )
    transcript_walt, beats_walt = _make_transcript_and_beats(
        ["Title Danny", "Beat1", "Beat2", "Quote Walt"]
    )
    beat_dummy = beats_walt[3]
    final_fixed, rep_fixed, _ = _evaluate_scene_critic(
        kq_init, beat_dummy, None, None, transcript_walt, b_test, backend_fixed, "", ""
    )
    assert rep_fixed.status == "mismatch_retried"
    assert rep_fixed.changed is True
    assert rep_fixed.repair is None
    assert isinstance(final_fixed, KineticQuoteScene)
    assert final_fixed.props.attribution_cast_id == "c3"
