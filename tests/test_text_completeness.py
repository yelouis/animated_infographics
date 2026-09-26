"""Unit tests for text completeness, LLM-facing schemas, and normalization.

Contract: design_planner.md §1, §6 item 7; design_testing_and_validation.md §2.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from animated_infographics.contracts.models import (
    AvatarConfig,
    Beat,
    Bible,
    CastMember,
)
from animated_infographics.contracts.templates import REGISTRY
from animated_infographics.planner.bible import BIBLE_SCHEMA
from animated_infographics.planner.critic import (
    build_critic_request,
)
from animated_infographics.planner.llm import llm_facing_schema
from animated_infographics.planner.props import _format_pydantic_validation_error
from animated_infographics.planner.validate import (
    normalize_text,
    text_complete_errors,
)
from animated_infographics.planner.voice import VOICE_SCHEMA

# ---------------------------------------------------------------------------
# 1. Text completeness test cases from design_testing_and_validation.md §2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text_input", "should_fail"),
    [
        ("...", True),
        ("Rescuers wade through waist-", True),
        ("Modern Era (", True),
        ("draws crowds at p", True),
        ("I was a young bride", False),
        ("$1,500 budget", False),
        ("Plan B", False),
    ],
)
def test_text_completeness_spec_cases(text_input: str, should_fail: bool) -> None:
    errors = text_complete_errors("props.text", text_input)
    if should_fail:
        assert len(errors) > 0, f"Expected '{text_input}' to be rejected as incomplete"
        assert "looks cut off" in errors[0]
    else:
        assert len(errors) == 0, f"Expected '{text_input}' to be accepted, got: {errors}"


def test_normalize_text_repairs_newline() -> None:
    raw = "Line one\nline two"
    repaired = normalize_text(raw)
    assert repaired == "Line one line two"
    errors = text_complete_errors("props.text", repaired)
    assert errors == []


# ---------------------------------------------------------------------------
# 2. Schema walk test: no length/pattern keys survive llm_facing_schema
# ---------------------------------------------------------------------------


FORBIDDEN_SCHEMA_KEYS = {"maxLength", "minLength", "maxItems", "minItems", "pattern"}
REQUIRED_SCHEMA_KEYS = {"enum", "type", "required", "additionalProperties"}


def walk_schema_keys(schema: Any) -> list[str]:
    found: list[str] = []
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k in FORBIDDEN_SCHEMA_KEYS:
                found.append(k)
            found.extend(walk_schema_keys(v))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(walk_schema_keys(item))
    return found


def test_llm_facing_schema_strips_forbidden_keys_all_templates() -> None:
    for name, spec in REGISTRY.items():
        raw_schema = spec.props_model.model_json_schema()
        clean = llm_facing_schema(raw_schema)
        forbidden_found = walk_schema_keys(clean)
        assert not forbidden_found, (
            f"Template {name} had forbidden keys in LLM-facing schema: {forbidden_found}"
        )


def test_llm_facing_schema_strips_forbidden_keys_bible_voice_critic() -> None:
    # 1. Bible schema
    clean_bible = llm_facing_schema(BIBLE_SCHEMA)
    assert not walk_schema_keys(clean_bible), "Bible schema retained forbidden keys"

    # 2. Voice schema
    clean_voice = llm_facing_schema(VOICE_SCHEMA)
    assert not walk_schema_keys(clean_voice), "Voice schema retained forbidden keys"
    # Verify enum survived
    assert clean_voice["properties"]["narrator_gender"]["enum"] == ["female", "male", "unknown"]

    # 3. Critic schemas (dialogue, text_thread, emotion_beat)
    avatar = AvatarConfig(
        skin=1,
        hair_style="short",
        hair_color="black",
        facial_hair="none",
        headwear="none",
        glasses=False,
        age="adult",
    )
    bible = Bible(
        schema_version=1,
        title="Test",
        logline="Test logline",
        genre="personal_story",
        cast=[
            CastMember(
                id="c1",
                name="Alice",
                role="lead",
                is_narrator=True,
                color_slot=0,
                avatar=avatar,
            )
        ],
        places=[],
        set_pieces=[],
    )
    beat = Beat(i=0, start_ms=0, end_ms=2000, text="Alice spoke.", word_start=0, word_end=2)

    # Dialogue critic
    from animated_infographics.contracts.models import DialogueScene
    from animated_infographics.contracts.templates import DialogueLine, DialogueProps

    diag_scene = DialogueScene(
        id="s001",
        beat_i=0,
        template="dialogue",
        props=DialogueProps(lines=[DialogueLine(cast_id="c1", text="Hello")]),
    )
    _, _, diag_schema = build_critic_request(diag_scene, beat, None, None, bible)
    clean_diag = llm_facing_schema(diag_schema)
    assert not walk_schema_keys(clean_diag), "Dialogue critic schema retained forbidden keys"

    # Text check schema (mock/draft representation)
    text_check_schema = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["letters_or_words", "none"]},
            "sample": {"type": "string", "maxLength": 20},
        },
        "required": ["kind", "sample"],
        "additionalProperties": False,
    }
    clean_tc = llm_facing_schema(text_check_schema)
    assert not walk_schema_keys(clean_tc), "Text check schema retained forbidden keys"
    assert clean_tc["properties"]["kind"]["enum"] == ["letters_or_words", "none"]


# ---------------------------------------------------------------------------
# 3. Pydantic retry message formatting for string_too_long
# ---------------------------------------------------------------------------


def test_retry_message_formatting() -> None:
    class Model(BaseModel):
        caption: str = Field(max_length=48)

    try:
        Model.model_validate({"caption": "A" * 61})
        pytest.fail("Should have failed validation")
    except ValidationError as exc:
        errs = [_format_pydantic_validation_error(e) for e in exc.errors()]
        assert len(errs) == 1
        expected_msg = (
            "props.caption: 61 characters, limit 48 — rewrite it shorter as a complete phrase"
        )
        assert errs[0] == expected_msg
