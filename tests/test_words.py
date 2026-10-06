"""Tests for word counting, WORD_CAPS contracts, and template classes."""

import typing
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from animated_infographics.contracts.templates import (
    KEPT_TEMPLATES,
    PICTURE_TEMPLATES,
    REGISTRY,
    REPLACEABLE_TEMPLATES,
    WORD_CAPS,
    CauseEffectNode,
    CauseEffectProps,
    CharacterIntroProps,
    ComparisonPanel,
    DialogueLine,
    DialogueProps,
    EmotionBeatProps,
    IconListItem,
    IconListProps,
    LocationProps,
    MapFocusProps,
    SetPieceProps,
    StatCalloutProps,
    TextMessage,
    TextThreadProps,
    TimelineEvent,
    TimelineProps,
)
from animated_infographics.planner.words import count_words, graphic_words


def test_removed_fields_and_list_maxima_raise():
    # Deleted fields must raise ValidationError
    with pytest.raises(ValidationError):
        StatCalloutProps.model_validate(
            {"value": 10.0, "caption": "historic liability", "suffix": "gallons"}
        )

    with pytest.raises(ValidationError):
        EmotionBeatProps.model_validate(
            {"cast_id": "c1", "emotion": "happy", "caption": "overjoyed"}
        )

    with pytest.raises(ValidationError):
        LocationProps.model_validate({"place_id": "p1", "caption": "estate on the lake"})

    with pytest.raises(ValidationError):
        SetPieceProps.model_validate({"set_piece_id": "v1", "caption": "secret box"})

    with pytest.raises(ValidationError):
        MapFocusProps.model_validate(
            {
                "region": "world",
                "markers": [{"place_id": "p1", "label": "Duluth"}],
                "caption": "from Duluth to Thunder Bay",
            }
        )

    with pytest.raises(ValidationError):
        CharacterIntroProps.model_validate(
            {"cast_id": "c1", "descriptor": "The manager", "traits": ["stern", "alert"]}
        )

    # List maxima must raise ValidationError when exceeded
    with pytest.raises(ValidationError):
        IconListProps(
            items=[
                IconListItem(icon="Drop", label="One"),
                IconListItem(icon="Drop", label="Two"),
                IconListItem(icon="Drop", label="Three"),
                IconListItem(icon="Drop", label="Four"),
            ]
        )

    with pytest.raises(ValidationError):
        CauseEffectProps(
            nodes=[
                CauseEffectNode(label="One"),
                CauseEffectNode(label="Two"),
                CauseEffectNode(label="Three"),
                CauseEffectNode(label="Four"),
            ]
        )

    with pytest.raises(ValidationError):
        ComparisonPanel(heading="Side A", points=["P1", "P2", "P3"])

    with pytest.raises(ValidationError):
        DialogueProps(
            lines=[
                DialogueLine(cast_id="c1", text="L1"),
                DialogueLine(cast_id="c2", text="L2"),
                DialogueLine(cast_id="c1", text="L3"),
            ]
        )

    with pytest.raises(ValidationError):
        TextThreadProps(
            contact_name="Bob",
            messages=[
                TextMessage(sender="them", text="M1"),
                TextMessage(sender="me", text="M2"),
                TextMessage(sender="them", text="M3"),
                TextMessage(sender="me", text="M4"),
            ],
        )

    with pytest.raises(ValidationError):
        TimelineProps(
            events=[
                TimelineEvent(date_label="1915", label="E1"),
                TimelineEvent(date_label="1916", label="E2"),
                TimelineEvent(date_label="1917", label="E3"),
                TimelineEvent(date_label="1918", label="E4"),
                TimelineEvent(date_label="1919", label="E5"),
            ],
            highlight_index=0,
        )


def _unwrap_type(t: Any) -> Any:
    """Unwrap Annotated and Optional/Union types down to base types."""
    origin = typing.get_origin(t)
    if origin is typing.Annotated:
        return _unwrap_type(typing.get_args(t)[0])
    if origin in (typing.Union, getattr(typing, "UnionType", None)):
        args = [arg for arg in typing.get_args(t) if arg is not type(None)]
        if len(args) == 1:
            return _unwrap_type(args[0])
    return t


def _resolve_field_type(model_cls: type[BaseModel], path: str) -> Any:
    parts = path.split(".")
    curr_type: Any = model_cls
    for part in parts:
        if part.endswith("[]"):
            field_name = part[:-2]
            fields = getattr(curr_type, "model_fields", {})
            assert field_name in fields, f"Field '{field_name}' not in {curr_type}"
            field_type = _unwrap_type(fields[field_name].annotation)
            origin = typing.get_origin(field_type)
            args = typing.get_args(field_type)
            assert origin in (list, tuple) and args, (
                f"Expected list/tuple type for {field_name}, got {field_type}"
            )
            curr_type = _unwrap_type(args[0])
        else:
            fields = getattr(curr_type, "model_fields", {})
            assert part in fields, f"Field '{part}' not in {curr_type}"
            curr_type = _unwrap_type(fields[part].annotation)
    return curr_type


def test_word_caps_paths_resolve():
    """Assert every path in WORD_CAPS resolves to str or str | None in that props model."""
    for template, caps in WORD_CAPS.items():
        spec = REGISTRY.get(template)
        assert spec is not None, f"Template '{template}' from WORD_CAPS not in REGISTRY"
        model_cls = spec.props_model
        for path in caps:
            resolved_type = _resolve_field_type(model_cls, path)
            assert resolved_type in (str, str | None), (
                f"Path '{path}' in template '{template}' resolved to {resolved_type}, "
                "expected str or str | None"
            )


def test_template_classes_partition_registry():
    """Assert PICTURE, REPLACEABLE, KEPT classes partition the 18 templates."""
    all_registry_templates = set(REGISTRY.keys())
    assert len(all_registry_templates) == 18

    # Pairwise disjoint
    assert PICTURE_TEMPLATES.isdisjoint(REPLACEABLE_TEMPLATES)
    assert PICTURE_TEMPLATES.isdisjoint(KEPT_TEMPLATES)
    assert REPLACEABLE_TEMPLATES.isdisjoint(KEPT_TEMPLATES)

    # Union equals all templates
    union_classes = PICTURE_TEMPLATES | REPLACEABLE_TEMPLATES | KEPT_TEMPLATES
    assert union_classes == all_registry_templates


def test_count_words():
    assert count_words("$1,500") == 1
    assert count_words("Mr. Alvarez") == 2
    assert count_words("— —") == 0
    assert count_words("Grandma Rose's pie") == 3
    assert count_words(None) == 0
    assert count_words("") == 0
    assert count_words("   ") == 0


def test_field_values_and_graphic_words():
    # Icon list
    icon_props = {
        "heading": "Historic Factors",
        "items": [
            {"icon": "Drop", "label": "Untested load"},
            {"icon": "Hammer", "label": "Rivets sheared"},
        ],
    }
    # heading: 2 words, items[0].label: 2 words, items[1].label: 2 words => total 6
    assert graphic_words("icon_list", icon_props) == 6

    # Templates without caps return 0
    assert graphic_words("title_card", {"title": "The Boston Molasses Flood"}) == 0
    assert graphic_words("emotion_beat", {"cast_id": "c1", "emotion": "neutral"}) == 0
    assert graphic_words("set_piece", {"set_piece_id": "v1"}) == 0

    # Stat callout: value line is excluded, suffix is counted
    stat_props = {
        "value": 2.3,
        "decimals": 1,
        "prefix": "",
        "display_scale": "million",
        "suffix": "gallons",
    }
    assert graphic_words("stat_callout", stat_props) == 1
