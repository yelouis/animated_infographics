"""Data contracts for presentation simulation evaluation and scoring.

Per design_presentation_simulation.md §8 and design_data_contracts.md.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PresentationMetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str
    value: float | None = None
    bar: float | str | None = None
    passed: bool


class PresentationScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    job_id: str
    level: str  # "mild" | "strong"
    style: str  # "literal" | "creative"
    slide_accuracy: float
    point_accuracy: float
    onset_lag_median_s: float | None = None
    onset_lag_p90_s: float | None = None
    false_switches_per_min: float
    adlib_stability: float
    skip_recovery_s: float | None = None
    all_passed: bool
    metrics: list[PresentationMetricResult] = Field(default_factory=list)
    density_words_per_s: float | None = None
    scene_criteria_clean: bool = True
    oracle: PresentationScore | None = None
