"""People-scene critic for detecting attribution, tone, and emotion meaning errors.

Contract: design_planner.md §11 (Issue 5 -> Option A, part 2).
"""

from typing import Any

from animated_infographics.contracts.models import (
    Beat,
    Bible,
    DialogueScene,
    EmotionBeatScene,
    KineticQuoteScene,
    Scene,
    TextThreadScene,
)

CRITIC_SYSTEM_PROMPT: str = (
    "You check who says or feels what in a story beat. "
    "Answer only from the text. Output JSON matching the schema."
)


def needs_critic(scene: Scene) -> bool:
    """Determine whether scene requires a blind critic check.

    Applies to dialogue, text_thread, emotion_beat, and kinetic_quote with
    attribution_cast_id. Never applies to deterministic fallback scenes.
    """
    if scene.rationale == "deterministic fallback":
        return False
    if isinstance(scene, (DialogueScene, TextThreadScene, EmotionBeatScene)):
        return True
    if isinstance(scene, KineticQuoteScene):
        return scene.props.attribution_cast_id is not None
    return False


def build_critic_request(
    scene: Scene,
    beat: Beat,
    prev_beat: Beat | None,
    next_beat: Beat | None,
    bible: Bible,
) -> tuple[str, str, dict[str, Any]]:
    """Build blind critic system prompt, user prompt, and JSON schema.

    Never includes proposed speaker, sender, tone, or emotion.
    """
    cast_lines: list[str] = []
    for c in bible.cast:
        narrator_tag = " [narrator]" if c.is_narrator else ""
        cast_lines.append(f"- {c.id}: {c.name} ({c.role}){narrator_tag}")
    cast_block = "\n".join(cast_lines)

    prev_text = prev_beat.text if prev_beat else "None (start of story)"
    next_text = next_beat.text if next_beat else "None (end of story)"

    context_block = (
        f"Cast:\n{cast_block}\n\n"
        f"Previous beat [context only]: {prev_text}\n"
        f"Current beat: {beat.text}\n"
        f"Next beat [context only]: {next_text}\n\n"
    )

    cast_ids = [c.id for c in bible.cast]

    if isinstance(scene, KineticQuoteScene):
        question = (
            f'Who wrote or said these quoted words: "{scene.props.text}" '
            'Answer a cast id, "narration" if they are the narrator telling the story, '
            'or "unknown".'
        )
        schema = {
            "type": "object",
            "properties": {
                "speaker": {
                    "type": "string",
                    "enum": [*cast_ids, "narration", "unknown"],
                }
            },
            "required": ["speaker"],
            "additionalProperties": False,
        }

    elif isinstance(scene, DialogueScene):
        lines_str = " ".join(
            f'{i + 1}. "{line_item.text}"' for i, line_item in enumerate(scene.props.lines)
        )
        question = (
            f"The scene shows these lines in order: {lines_str} "
            'For each line, who says it (cast id or "unknown") and in what tone?'
        )
        schema = {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {
                                "type": "string",
                                "enum": [*cast_ids, "unknown"],
                            },
                            "tone": {
                                "type": "string",
                                "enum": [
                                    "neutral",
                                    "angry",
                                    "happy",
                                    "sad",
                                    "shocked",
                                    "sarcastic",
                                    "unknown",
                                ],
                            },
                        },
                        "required": ["speaker", "tone"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["lines"],
            "additionalProperties": False,
        }

    elif isinstance(scene, TextThreadScene):
        msgs_str = " ".join(f'{i + 1}. "{m.text}"' for i, m in enumerate(scene.props.messages))
        question = (
            f"The phone belongs to the narrator. Messages in order: {msgs_str} "
            'For each, was it sent by the narrator ("me") or the other person ("them")?'
        )
        schema = {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sender": {
                                "type": "string",
                                "enum": ["me", "them", "unknown"],
                            }
                        },
                        "required": ["sender"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["messages"],
            "additionalProperties": False,
        }

    elif isinstance(scene, EmotionBeatScene):
        question = "Which cast member feels something in this beat, and what is the main feeling?"
        schema = {
            "type": "object",
            "properties": {
                "cast_id": {
                    "type": "string",
                    "enum": [*cast_ids, "unknown"],
                },
                "emotion": {
                    "type": "string",
                    "enum": [
                        "happy",
                        "sad",
                        "angry",
                        "shocked",
                        "confused",
                        "smug",
                        "nervous",
                        "unknown",
                    ],
                },
            },
            "required": ["cast_id", "emotion"],
            "additionalProperties": False,
        }

    else:
        raise ValueError(f"Critic request not supported for template: {scene.template}")

    user_prompt = context_block + question
    return CRITIC_SYSTEM_PROMPT, user_prompt, schema


def validate_critic_answer(
    scene: Scene, answer: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Validate critic answer conforms to expected structure and item counts."""
    errors: list[str] = []

    if isinstance(scene, DialogueScene):
        lines = answer.get("lines")
        if not isinstance(lines, list) or len(lines) != len(scene.props.lines):
            got_len = len(lines) if isinstance(lines, list) else "non-list"
            errors.append(
                f"critic lines length mismatch: expected {len(scene.props.lines)}, got {got_len}"
            )

    elif isinstance(scene, TextThreadScene):
        messages = answer.get("messages")
        if not isinstance(messages, list) or len(messages) != len(scene.props.messages):
            got_len = len(messages) if isinstance(messages, list) else "non-list"
            errors.append(
                f"critic messages length mismatch: expected {len(scene.props.messages)}, "
                f"got {got_len}"
            )

    return answer, errors


def critic_mismatches(scene: Scene, answer: dict[str, Any], bible: Bible) -> list[str]:
    """Compare candidate props with critic reading according to §11 deterministic rules.

    Rules:
    - Who (speaker, sender, cast_id): mismatch iff critic value != "unknown" and != props.
      For kinetic_quote, "narration" agrees only with the narrator's cast id.
      Critic "unknown" is NEVER a mismatch for who.
    - Dialogue tone: mismatch iff (critic tone != "unknown" and != props tone) or
      (critic tone == "unknown" and props tone != "neutral").
    - Emotion: mismatch iff critic emotion != "unknown" and != props emotion.

    Returns:
        List of formatted mismatch strings, e.g. ["lines[0].tone: angry vs unknown"].
    """
    mismatches: list[str] = []
    narrator = next((c for c in bible.cast if c.is_narrator), None)
    narrator_id = narrator.id if narrator else None

    if isinstance(scene, KineticQuoteScene):
        props_val = scene.props.attribution_cast_id
        critic_val = answer.get("speaker")
        if critic_val == "narration":
            if props_val != narrator_id:
                mismatches.append(f"attribution_cast_id: {props_val} vs {critic_val}")
        elif critic_val is not None and critic_val != "unknown" and critic_val != props_val:
            mismatches.append(f"attribution_cast_id: {props_val} vs {critic_val}")

    elif isinstance(scene, DialogueScene):
        answer_lines = answer.get("lines", [])
        for i, line in enumerate(scene.props.lines):
            if i >= len(answer_lines):
                break
            ans_line = answer_lines[i]
            critic_speaker = ans_line.get("speaker")
            if (
                critic_speaker is not None
                and critic_speaker != "unknown"
                and critic_speaker != line.cast_id
            ):
                mismatches.append(f"lines[{i}].cast_id: {line.cast_id} vs {critic_speaker}")

            critic_tone = ans_line.get("tone")
            if (critic_tone != "unknown" and critic_tone != line.tone) or (
                critic_tone == "unknown" and line.tone != "neutral"
            ):
                mismatches.append(f"lines[{i}].tone: {line.tone} vs {critic_tone}")

    elif isinstance(scene, TextThreadScene):
        answer_msgs = answer.get("messages", [])
        for i, msg in enumerate(scene.props.messages):
            if i >= len(answer_msgs):
                break
            ans_msg = answer_msgs[i]
            critic_sender = ans_msg.get("sender")
            if (
                critic_sender is not None
                and critic_sender != "unknown"
                and critic_sender != msg.from_
            ):
                mismatches.append(f"messages[{i}].from: {msg.from_} vs {critic_sender}")

    elif isinstance(scene, EmotionBeatScene):
        critic_cast = answer.get("cast_id")
        if (
            critic_cast is not None
            and critic_cast != "unknown"
            and critic_cast != scene.props.cast_id
        ):
            mismatches.append(f"cast_id: {scene.props.cast_id} vs {critic_cast}")

        critic_emotion = answer.get("emotion")
        if (
            critic_emotion is not None
            and critic_emotion != "unknown"
            and critic_emotion != scene.props.emotion
        ):
            mismatches.append(f"emotion: {scene.props.emotion} vs {critic_emotion}")

    return mismatches


def format_disagreement_message(mismatches: list[str]) -> str:
    """Format the §11 disagreement message appended to retry prompt."""
    lines: list[str] = []
    for m in mismatches:
        if ":" in m and " vs " in m:
            field, rest = m.split(":", 1)
            val1, val2 = rest.split(" vs ", 1)
            lines.append(
                f"- {field.strip()}: you said {val1.strip()}; the reading says {val2.strip()}"
            )
        else:
            lines.append(f"- {m}")
    bullet_block = "\n".join(lines)
    return (
        "A second, independent reading of this beat disagrees:\n"
        f"{bullet_block}\n"
        "Fix the props if that reading fits the beat text better; otherwise keep yours."
    )
