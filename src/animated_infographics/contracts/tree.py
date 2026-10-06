"""Data contracts for presentation animation tree.

Per design_presentation_simulation.md §3 and design_data_contracts.md §10.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from animated_infographics.contracts.models import SceneUnion


class TreeNode(BaseModel):
    """A node in the presentation animation tree."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slide: str
    kind: Literal["section", "point"]
    point_i: int | None = None
    text: str
    scene: SceneUnion


class TreeEdge(BaseModel):
    """A directed edge in the presentation animation tree with transition cost."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    kind: Literal["next", "skip", "back"]
    cost: float = Field(ge=0.0)


class TreePlan(BaseModel):
    """Complete presentation animation tree with nodes and edges."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    nodes: list[TreeNode]
    edges: list[TreeEdge]


AnimationTree = TreePlan
