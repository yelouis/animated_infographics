"""Slow integration tests for narrator voice selection with live gemma4:26b."""

import json
from pathlib import Path

import pytest

from animated_infographics.planner.llm import OllamaBackend
from animated_infographics.planner.voice import select_voice


def _parse_script(path: Path) -> tuple[str | None, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip() and not lines[1].strip():
        title = lines[0].strip()
        body = "\n".join(lines[2:])
        return title, body
    return None, text


@pytest.mark.slow
def test_voice_all_four_fixtures() -> None:
    """Verify narrator voice decisions on all 4 fixtures match expected JSONs."""
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

    fixtures = ["molasses_flood", "emu_war", "story_recipe_box", "story_room_12"]

    for name in fixtures:
        script_path = fixtures_dir / "scripts" / f"{name}.txt"
        expected_path = fixtures_dir / "expected" / f"{name}.json"

        title, body = _parse_script(script_path)
        with open(expected_path, encoding="utf-8") as f:
            expected = json.load(f)

        backend = OllamaBackend(no_cache=True)
        decision = select_voice(title, body, flag_voice=None, backend=backend)

        assert decision.voice == expected["voice"], (
            f"{name}: expected voice {expected['voice']}, got {decision.voice}"
        )
        assert decision.reason == expected["voice_reason"], (
            f"{name}: expected reason {expected['voice_reason']}, got {decision.reason}"
        )

        if expected.get("evidence_contains"):
            assert decision.evidence is not None, f"{name}: expected evidence, got None"
            msg = f"{name}: expected '{expected['evidence_contains']}' in '{decision.evidence}'"
            assert expected["evidence_contains"] in decision.evidence, msg

        if name in {"molasses_flood", "emu_war"}:
            assert backend.calls == 0, f"{name}: third person must make zero backend calls"


@pytest.mark.slow
def test_voice_inline_snippets() -> None:
    """Verify inline test snippets for unknown and male narrators."""
    backend = OllamaBackend(no_cache=True)

    # Snippet 1: occupation and family mentions, but no self-identification
    snippet_1 = (
        "My sister is a nurse and my mom is a teacher. "
        "I work nights at the hospital and I love my job."
    )
    dec1 = select_voice(None, snippet_1, flag_voice=None, backend=backend)
    assert dec1.narrator_gender == "unknown"
    assert dec1.voice == "am_michael"

    # Snippet 2: "As a dad of three, I" self-identifies male
    snippet_2 = "As a dad of three, I never thought I'd be asked to leave a playground."
    dec2 = select_voice(None, snippet_2, flag_voice=None, backend=backend)
    assert dec2.narrator_gender == "male"
    assert dec2.voice == "am_michael"
