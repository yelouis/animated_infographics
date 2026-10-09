"""Data contracts for presentation anticipation.

Per design_presentation_simulation.md §6.6.1 and agent_execution_guide.md §1.3 (J2).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnticipationPlan(BaseModel):
    """Anticipated speech for presentation tree nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    nodes: dict[str, list[str]]
