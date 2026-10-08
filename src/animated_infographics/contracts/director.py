"""Pydantic v2 data models for Director contracts.

Per design_styles.md §3.3 and design_data_contracts.md §10.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MotifAppearance(BaseModel):
    """Single appearance of a recurring motif token or scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    beat_i: int
    role: Literal["plant", "echo", "payoff"]


class MotifDirective(BaseModel):
    """Recurring motif specification across the video."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    icon: str | None = None
    set_piece_id: str | None = None
    appearances: list[MotifAppearance] = Field(default_factory=list)


class MetaphorDirective(BaseModel):
    """Visual metaphor directive for a beat."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    beat_i: int
    image: str
    label: str | None = None
    cast_ids: list[str] = Field(default_factory=list)


class AsideDirective(BaseModel):
    """Visual gag or aside overlay directive for a beat."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    beat_i: int
    kind: Literal["thought", "label", "prop"]
    icon: str | None = None
    text: str | None = None
    cast_id: str | None = None


class LicenseDropped(BaseModel):
    """Record of an item dropped by the license critic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item: dict[str, Any]
    verdict: str


class OverlayDropped(BaseModel):
    """Record of an overlay dropped during timeline compilation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item: dict[str, Any]
    reason: str


class DirectorDropped(BaseModel):
    """Record of an item dropped by director salvage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item: str
    error: str


class DirectorPlan(BaseModel):
    """Whole-story creative plan produced by the director stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    motifs: list[MotifDirective] = Field(default_factory=list)
    metaphors: list[MetaphorDirective] = Field(default_factory=list)
    asides: list[AsideDirective] = Field(default_factory=list)
    license_dropped: list[LicenseDropped] = Field(default_factory=list)
    overlay_dropped: list[OverlayDropped] = Field(default_factory=list)
    director_dropped: list[DirectorDropped] = Field(default_factory=list)
