"""Unit tests for planner/voice.py narrator voice selection and rule verification."""

from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.planner.voice import (
    decide_voice,
    find_narrator_tag,
    first_person_rate,
    select_voice,
    self_identifying_token,
    strip_quoted,
    validate_gender_answer,
)


class DummyBackend:
    """Mock backend tracking calls for unit tests."""

    def __init__(self, response: dict[str, Any] | None = None, fail: bool = False) -> None:
        self.response = response or {"narrator_gender": "unknown", "evidence": None}
        self.fail = fail
        self.calls: int = 0
        self.cache_hits: int = 0

    def generate_json(
        self,
        *,
        stage: str,
        messages: list[dict[str, str]] | None = None,
        system: str | None = None,
        user: str | None = None,
        schema: dict[str, Any],
        attempt: int,
    ) -> dict[str, Any]:
        self.calls += 1
        if self.fail:
            raise ValueError("Backend forced failure")
        return self.response


def test_fixture_first_person_rates() -> None:
    """Verify first-person rate on all four fixtures equals measured values (±0.01)."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "scripts"

    recipe_text = (fixtures_dir / "story_recipe_box.txt").read_text(encoding="utf-8")
    rate_recipe = first_person_rate(recipe_text)
    assert abs(rate_recipe - 5.45) <= 0.01

    rate_room = first_person_rate((fixtures_dir / "story_room_12.txt").read_text(encoding="utf-8"))
    assert abs(rate_room - 3.67) <= 0.01

    molasses_text = (fixtures_dir / "molasses_flood.txt").read_text(encoding="utf-8")
    rate_molasses = first_person_rate(molasses_text)
    assert abs(rate_molasses - 0.00) <= 0.01

    rate_emu = first_person_rate((fixtures_dir / "emu_war.txt").read_text(encoding="utf-8"))
    assert abs(rate_emu - 0.00) <= 0.01


def test_first_person_rate_only_inside_quotes() -> None:
    """Verify a text whose only 'I' is inside double quotes counts as third person."""
    text = (
        'He shook his head and said, "I will never agree to this terms, because I am proud." '
        "Then he left."
    )
    assert strip_quoted(text) == "He shook his head and said,  Then he left."
    rate = first_person_rate(text)
    assert rate == 0.0


def test_find_narrator_tag() -> None:
    """Verify Reddit narrator tag detection on various forms."""
    tag1 = find_narrator_tag("I (26F) had an argument with my neighbor.")
    assert tag1 == ("female", "I (26F)")

    tag2 = find_narrator_tag("My (34M) wife (33F) refused to go.")
    assert tag2 == ("male", "My (34M)")

    tag3 = find_narrator_tag("Me [F29] waiting for the bus.")
    assert tag3 == ("female", "Me [F29]")

    # Tag on someone else -> no narrator tag
    tag_other = find_narrator_tag("My sister (22F) said she would help.")
    assert tag_other is None


EVIDENCE_TEST_CASES = [
    ("I'm a first-time mom", "female", "mom"),
    ("As the only granddaughter, I got Grandma Rose's recipe box", "female", "granddaughter"),
    ("Being the oldest daughter, I", "female", "daughter"),
    ("I'm a 30-year-old woman", "female", "woman"),
    ("I was a young bride", "female", "bride"),
    ("She called me selfish, and as a sister I felt awful", "female", "sister"),
    ("As a dad of three, I never thought", "male", "dad"),
    ("I got Grandma Rose's recipe box", "female", None),
    ("My sister Maya", "female", None),
    ("my mother-in-law, Linda", "female", None),
    ("Mom said family doesn't send invoices", "female", None),
    ("I'm her daughter", "female", None),  # † possessive
    ("I'm Maya's sister", "female", None),
    ("I'm the bride's cousin", "female", None),
    ("I am the Queen of this house", "female", None),  # † lowercase
    ("I'm sister Maya's favourite", "female", None),  # † title before name
    ("She treated me as a sister for years", "female", None),  # † Form B without following I
    ("a woman walked in holding a small suitcase I recognized", "female", None),
    ("When I met the bride at the door", "female", None),
    ("texted my wife to make sure she was still awake", "female", None),
    ("texted my wife to make sure she was still awake", "male", None),
    ("I did crosswords, knitted scarves nobody asked for", "female", None),
    ("As my sister Maya said, I was wrong", "female", None),
    ("My brother Danny got her house", "male", None),
]


@pytest.mark.parametrize("evidence,gender,expected", EVIDENCE_TEST_CASES)
def test_all_23_evidence_cases(
    evidence: str, gender: Literal["female", "male"], expected: str | None
) -> None:
    """Verify all 23 design-time evidence cases for self_identifying_token."""
    token = self_identifying_token(evidence, gender)
    assert token == expected


def test_validate_gender_answer_repairs_and_verbatim() -> None:
    """Verify validate_gender_answer repairs unknown evidence and checks verbatim span."""
    text = "As the only granddaughter, I got Grandma Rose's recipe box."

    # Valid female answer
    valid_ans, errs = validate_gender_answer(
        text,
        {"narrator_gender": "female", "evidence": "As the only granddaughter, I"},
    )
    assert errs == []
    assert valid_ans["evidence"] == "As the only granddaughter, I"

    # Evidence not in text -> error
    bad_span_ans, errs_span = validate_gender_answer(
        text,
        {"narrator_gender": "female", "evidence": "As the only granddaughter, I said"},
    )
    assert len(errs_span) == 1
    assert "verbatim span" in errs_span[0]

    # unknown with non-null evidence -> repaired to None with 0 errors
    unknown_ans, errs_unk = validate_gender_answer(
        text,
        {"narrator_gender": "unknown", "evidence": "I got Grandma Rose's recipe box"},
    )
    assert errs_unk == []
    assert unknown_ans["evidence"] is None


@pytest.mark.parametrize(
    "perspective,gender,expected_voice",
    [
        ("first_person", "female", "af_heart"),
        ("first_person", "male", "am_michael"),
        ("first_person", "unknown", "am_michael"),
        ("third_person", "female", "am_michael"),
        ("third_person", "male", "am_michael"),
        ("third_person", "unknown", "am_michael"),
    ],
)
def test_decide_voice_truth_table(perspective: str, gender: str, expected_voice: str) -> None:
    """Verify 6-row truth table for decide_voice: only first_person female is af_heart."""
    assert decide_voice(perspective, gender) == expected_voice


def test_flag_voice_zero_backend_calls() -> None:
    """Verify --voice am_michael makes zero backend calls."""
    backend = DummyBackend()
    decision = select_voice(
        title="Some title",
        body="I was a young bride and I loved my life very much.",
        flag_voice="am_michael",
        backend=backend,
    )
    assert backend.calls == 0
    assert decision.voice == "am_michael"
    assert decision.source == "flag"
    assert decision.reason == "flag"


def test_invalid_voice_rejected() -> None:
    """Verify voice outside installed voices is rejected."""
    with pytest.raises(ValidationError):
        VoiceDecision(voice="bm_george", source="flag", reason="flag")  # type: ignore[arg-type]


def test_backend_failure_falls_back_to_unknown_am_michael() -> None:
    """Verify a backend that fails 3 times falls back to unknown/no_evidence/am_michael."""
    backend = DummyBackend(fail=True)
    body = "I am writing this story because I think about it every single day of my life."
    decision = select_voice(
        title="My Story",
        body=body,
        flag_voice=None,
        backend=backend,
    )
    assert decision.voice == "am_michael"
    assert decision.reason == "no_evidence"
    assert decision.narrator_gender == "unknown"
    assert decision.evidence is None
