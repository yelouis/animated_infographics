"""Data contracts for presentation playback.

Per design_presentation_simulation.md §6.5 and agent_execution_guide.md §1.3 (H4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlaybackCommit(BaseModel):
    """A commit of a tree node to display during presentation playback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    at_ms: int = Field(ge=0)
    decision_ms: int = Field(ge=0)
    compute_ms: int = Field(ge=0)
    score: float
    runner_up_id: str | None = None
    runner_up_gap: float | None = None
    tiebreak_used: bool = False

    @property
    def node(self) -> str:
        return self.node_id

    @property
    def start_ms(self) -> int:
        return self.at_ms

    @property
    def decided_ms(self) -> int:
        return self.decision_ms

    @property
    def latency_ms(self) -> int:
        return self.compute_ms

    @property
    def score_margin(self) -> float | None:
        return self.runner_up_gap


class PlaybackHold(BaseModel):
    """A hold decision where no node switch occurred."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_ms: int = Field(ge=0)
    current_node_id: str
    top_candidate_id: str
    top_candidate_score: float
    reason: str


class PlaybackPlan(BaseModel):
    """Complete presentation playback record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    commits: list[PlaybackCommit]
    holds: list[PlaybackHold] = Field(default_factory=list)
