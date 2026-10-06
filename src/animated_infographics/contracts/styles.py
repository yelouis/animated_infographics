"""Style specifications and registry.

Per design_styles.md §1–3.
"""

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

StyleName = Literal["literal", "creative"]
StyleLicense = Literal["none", "small_embellishments"]

LITERAL_TEMPLATES: Final[list[str]] = [
    "title_card",
    "kinetic_quote",
    "stat_callout",
    "icon_list",
    "reveal",
    "cause_effect",
    "comparison",
    "character_intro",
    "dialogue",
    "text_thread",
    "emotion_beat",
    "relationship_map",
    "location",
    "set_piece",
    "map_focus",
    "timeline",
]

CREATIVE_TEMPLATES: Final[list[str]] = [
    *LITERAL_TEMPLATES,
    "metaphor",
    "callback",
]


class StyleSpec(BaseModel):
    """Specification of a visual style."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: StyleName
    director: bool
    templates: list[str]
    overlays: bool
    license: StyleLicense


STYLES: Final[dict[str, StyleSpec]] = {
    "literal": StyleSpec(
        name="literal",
        director=False,
        templates=LITERAL_TEMPLATES,
        overlays=False,
        license="none",
    ),
    "creative": StyleSpec(
        name="creative",
        director=True,
        templates=CREATIVE_TEMPLATES,
        overlays=True,
        license="small_embellishments",
    ),
}
