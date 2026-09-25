"""Exception types mapped to CLI exit codes."""


class InfographicsError(Exception):
    """Base exception for animated_infographics."""


class ValidationFailed(InfographicsError):
    """Validation failure (bad inputs, bad options, invalid plan) -> exit 2."""


class GateRefused(InfographicsError):
    """Gate refusal (wrong state, plan hash mismatch) -> exit 3."""


class DependencyMissing(InfographicsError):
    """Missing system or model dependency -> exit 4."""
