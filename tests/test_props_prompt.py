"""Unit tests for allowed icon names in the props prompt per E4 (design_planner.md §5)."""

from pathlib import Path
from typing import Any, get_args

from animated_infographics.contracts.icons import IconName
from animated_infographics.contracts.models import (
    Beat,
    Bible,
    Transcript,
    TranscriptSentence,
    TranscriptWord,
)
from animated_infographics.planner.llm import LLMBackend
from animated_infographics.planner.props import plan_single_template_props


class CapturingBackend(LLMBackend):
    def __init__(self, canned_response: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.canned_response = canned_response or {}
        self.captured_user_prompts: list[str] = []

    def generate_json(
        self, *, stage: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
        self.captured_user_prompts.append(user_msg)
        return self.canned_response


def test_icon_prompt_block_appended_for_icon_templates() -> None:
    """Verify icon prompt block is appended for templates with icons, and absent for others."""
    icon_names_str = ", ".join(get_args(IconName))
    expected_block = (
        "\n\n# Icons\n"
        "Every icon field must be one of these names. Pick the one that depicts the label; "
        "if none does and the field is optional, leave it out.\n"
        f"{icon_names_str}"
    )

    bible = Bible(
        schema_version=1,
        title="Test Story",
        logline="Logline",
        genre="history",
        cast=[],
        places=[],
        set_pieces=[],
    )
    words = [TranscriptWord(i=0, text="Hello", start_ms=0, end_ms=1000, sentence_i=0)]
    sentences = [
        TranscriptSentence(
            i=0,
            text="Hello world.",
            start_ms=0,
            end_ms=1000,
            word_start=0,
            word_end=1,
            paragraph_i=0,
            is_title=False,
        )
    ]
    transcript = Transcript(
        schema_version=1,
        source="tts",
        audio_path="test.wav",
        duration_ms=1000,
        words=words,
        sentences=sentences,
    )
    beat = Beat(i=1, word_start=0, word_end=1, start_ms=0, end_ms=1000, text="Hello world.")

    prompt_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "animated_infographics"
        / "planner"
        / "prompts"
        / "props.md"
    )
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # 1. Templates with icon fields: stat_callout, icon_list, cause_effect, comparison
    icon_templates = ["stat_callout", "icon_list", "cause_effect", "comparison"]
    for tmpl in icon_templates:
        backend = CapturingBackend()
        plan_single_template_props(
            template_name=tmpl,
            scene_id="s001",
            beat_i=1,
            beat=beat,
            prev_beat=None,
            next_beat=None,
            transcript=transcript,
            bible=bible,
            backend=backend,
            prompt_template=prompt_template,
            compact_bible="compact bible",
        )
        assert len(backend.captured_user_prompts) >= 1
        user_prompt = backend.captured_user_prompts[0]
        assert user_prompt.endswith(expected_block), (
            f"Template '{tmpl}' prompt does not end with expected icon block"
        )

    # 2. Templates without icon fields: kinetic_quote, reveal, timeline, etc.
    non_icon_templates = ["kinetic_quote", "reveal", "timeline"]
    for tmpl in non_icon_templates:
        backend = CapturingBackend()
        plan_single_template_props(
            template_name=tmpl,
            scene_id="s001",
            beat_i=1,
            beat=beat,
            prev_beat=None,
            next_beat=None,
            transcript=transcript,
            bible=bible,
            backend=backend,
            prompt_template=prompt_template,
            compact_bible="compact bible",
        )
        assert len(backend.captured_user_prompts) >= 1
        user_prompt = backend.captured_user_prompts[0]
        assert "# Icons" not in user_prompt, (
            f"Template '{tmpl}' should not contain icon prompt block"
        )
