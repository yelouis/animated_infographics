"""Pydantic v2 data models for Presentation Deck contracts.

Per design_presentation_simulation.md §2 and design_data_contracts.md §10.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeckPoint(BaseModel):
    """Talking point on a slide, mapped to script sentences."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    sentence_ids: list[int] = Field(default_factory=list)


class DeckSlide(BaseModel):
    """Presentation slide containing talking points."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    points: list[DeckPoint] = Field(default_factory=list)
    sentence_ids: list[int] = Field(default_factory=list)


class DeckPlan(BaseModel):
    """Whole-presentation slide deck plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    slides: list[DeckSlide] = Field(default_factory=list)


Deck = DeckPlan
