"""Narrator voice selection and first-person gender identification."""

import re
from functools import partial
from pathlib import Path
from typing import Any, Final, Literal

from animated_infographics.contracts.models import VoiceDecision
from animated_infographics.planner.grounding import is_verbatim_span
from animated_infographics.planner.llm import LLMBackend, run_with_retries

VOICE_DEFAULT: Final[Literal["am_michael"]] = "am_michael"
VOICE_FEMALE_NARRATOR: Final[Literal["af_heart"]] = "af_heart"
INSTALLED_VOICES: Final[frozenset[str]] = frozenset({"af_heart", "am_michael"})

FIRST_PERSON_TOKENS: Final[frozenset[str]] = frozenset(
    {"i", "i'm", "i've", "i'd", "i'll", "me", "my", "mine", "myself"}
)
FIRST_PERSON_RATE_MIN: Final[float] = 2.0

POSSESSIVES: Final[frozenset[str]] = frozenset({"my", "our", "your", "his", "her", "their", "its"})

FEMALE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "woman",
        "women",
        "girl",
        "wife",
        "mother",
        "mom",
        "mum",
        "mommy",
        "daughter",
        "sister",
        "aunt",
        "niece",
        "girlfriend",
        "bride",
        "lady",
        "fiancee",
        "fiancée",
        "grandmother",
        "grandma",
        "granddaughter",
        "queen",
        "princess",
        "stepmother",
        "stepmom",
        "stepdaughter",
        "female",
    }
)

MALE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "man",
        "men",
        "guy",
        "boy",
        "husband",
        "father",
        "dad",
        "daddy",
        "son",
        "brother",
        "uncle",
        "nephew",
        "boyfriend",
        "groom",
        "gentleman",
        "fiance",
        "fiancé",
        "grandfather",
        "grandpa",
        "grandson",
        "king",
        "prince",
        "stepfather",
        "stepdad",
        "stepson",
        "male",
    }
)

SUBJ_TOKENS: Final[frozenset[str]] = frozenset({"I", "I'm", "I've", "I'd"})

NARRATOR_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(I|I'm|me|my|myself)\s*[\(\[]\s*(?:(\d{1,2})\s*([FfMm])|([FfMm])\s*(\d{1,2}))\s*[\)\]]",
    re.IGNORECASE,
)

VOICE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "narrator_gender": {
            "type": "string",
            "enum": ["female", "male", "unknown"],
        },
        "evidence": {
            "type": ["string", "null"],
            "maxLength": 160,
        },
    },
    "required": ["narrator_gender", "evidence"],
    "additionalProperties": False,
}


def strip_quoted(text: str) -> str:
    """Normalize curly quotes to straight quotes and drop every double-quoted span."""
    # Convert curly double quotes to straight double quotes
    t = text.replace("“", '"').replace("”", '"')
    # Drop all double-quoted spans
    return re.sub(r'"[^"]*"', "", t)


def first_person_rate(text: str) -> float:
    """Calculate first-person tokens per 100 words on unquoted text.

    first_person_rate = round(100 * |tokens in FIRST_PERSON_TOKENS| / |tokens|, 2)
    """
    stripped = strip_quoted(text)
    tokens = [t.lower() for t in re.findall(r"[A-Za-z']+", stripped)]
    if not tokens:
        return 0.0
    fp_count = sum(1 for t in tokens if t in FIRST_PERSON_TOKENS)
    return round(100.0 * fp_count / len(tokens), 2)


def find_narrator_tag(text: str) -> tuple[Literal["female", "male"], str] | None:
    """Find Reddit-style narrator age/gender tag on unstripped text."""
    m = NARRATOR_TAG_RE.search(text)
    if not m:
        return None

    g3, g4 = m.group(3), m.group(4)
    letter = (g3 or g4).upper()
    gender: Literal["female", "male"] = "female" if letter == "F" else "male"
    evidence = m.group(0)
    return gender, evidence


# ---------------------------------------------------------------------------
# Four separately named candidate checks for self_identifying_token
# ---------------------------------------------------------------------------


def check_lowercase(token: str) -> bool:
    """Check 1: candidate is written in lowercase (avoids Grandma, Mom, Queen)."""
    return token == token.lower()


def check_lexicon(token: str, gender: Literal["female", "male"]) -> bool:
    """Check 2: candidate or its part before first hyphen is in the gender lexicon."""
    head = token.split("-")[0].lower()
    lexicon = FEMALE_TOKENS if gender == "female" else MALE_TOKENS
    return head in lexicon


def check_no_possessive_before(prev_token: str | None) -> bool:
    """Check 3: preceding token is not a possessive and does not end in 's."""
    if prev_token is None:
        return True
    p = prev_token.lower()
    if p in POSSESSIVES or p.endswith("'s"):
        return False
    return True


def check_no_uppercase_after(next_token: str | None) -> bool:
    """Check 4: succeeding token does not start with uppercase unless in SUBJ."""
    if next_token is None:
        return True
    if next_token in SUBJ_TOKENS:
        return True
    return not next_token[0].isupper()


def self_identifying_token(evidence: str, gender: Literal["female", "male"]) -> str | None:
    """Extract first valid self-identifying token of the claimed gender from evidence."""
    clauses = re.split(r"[.!?;\:]", evidence)

    for clause in clauses:
        tokens = re.findall(r"[A-Za-z0-9'\-éÉ]+", clause)
        n = len(tokens)

        # Scan for Form A (copula)
        for i in range(n):
            t = tokens[i]
            form_a_end: int | None = None

            if t == "I'm":
                form_a_end = i
            elif t == "I" and i + 1 < n and tokens[i + 1].lower() in {"am", "was", "became"}:
                form_a_end = i + 1
            elif t == "I've" and i + 1 < n and tokens[i + 1].lower() == "been":
                form_a_end = i + 1

            if form_a_end is not None:
                # Next 4 tokens are candidates
                for c_idx in range(form_a_end + 1, min(n, form_a_end + 5)):
                    candidate = tokens[c_idx]
                    prev_t = tokens[c_idx - 1] if c_idx > 0 else None
                    next_t = tokens[c_idx + 1] if c_idx + 1 < n else None

                    if (
                        check_lowercase(candidate)
                        and check_lexicon(candidate, gender)
                        and check_no_possessive_before(prev_t)
                        and check_no_uppercase_after(next_t)
                    ):
                        return candidate

        # Scan for Form B (as / being)
        for i in range(n):
            if tokens[i].lower() in {"as", "being"}:
                # Next 4 tokens are candidates
                for c_idx in range(i + 1, min(n, i + 5)):
                    candidate = tokens[c_idx]

                    # Requirement: a SUBJ token must occur within the 4 tokens after candidate
                    following = tokens[c_idx + 1 : min(n, c_idx + 5)]
                    if not any(ft in SUBJ_TOKENS for ft in following):
                        continue

                    prev_t = tokens[c_idx - 1] if c_idx > 0 else None
                    next_t = tokens[c_idx + 1] if c_idx + 1 < n else None

                    if (
                        check_lowercase(candidate)
                        and check_lexicon(candidate, gender)
                        and check_no_possessive_before(prev_t)
                        and check_no_uppercase_after(next_t)
                    ):
                        return candidate

    return None


def validate_gender_answer(text: str, answer: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate LLM gender decision response."""
    gender = answer.get("narrator_gender")
    evidence = answer.get("evidence")

    if gender not in {"female", "male", "unknown"}:
        return answer, [f"narrator_gender must be female, male, or unknown; got '{gender}'"]

    # Rule a: repair unknown with evidence -> evidence: null
    if gender == "unknown":
        if evidence is not None:
            answer = dict(answer)
            answer["evidence"] = None
        return answer, []

    # Rule b: female/male requires non-null evidence that is a verbatim span
    if not evidence or not isinstance(evidence, str):
        return answer, [f"narrator_gender '{gender}' requires non-null string evidence"]

    if not is_verbatim_span(evidence, text):
        return answer, ["evidence must be a verbatim span of the text"]

    # Rule c: evidence must contain a self-identifying token of the claimed gender
    token = self_identifying_token(evidence, gender)  # type: ignore[arg-type]
    if token is None:
        return answer, [f"evidence contains no self-identifying token for gender '{gender}'"]

    return answer, []


def decide_voice(perspective: str, gender: str) -> Literal["af_heart", "am_michael"]:
    """Decide voice from perspective and gender: only first_person female -> af_heart."""
    if perspective == "first_person" and gender == "female":
        return VOICE_FEMALE_NARRATOR
    return VOICE_DEFAULT


def load_prompt(name: str) -> str:
    """Load prompt template from planner/prompts/ directory."""
    prompt_path = Path(__file__).parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")


def select_voice(
    title: str | None,
    body: str,
    *,
    flag_voice: str | None,
    backend: LLMBackend,
) -> VoiceDecision:
    """Select narrator voice following the 5-step decision algorithm."""
    # Step 1: Flag override
    if flag_voice is not None:
        return VoiceDecision(
            voice=flag_voice,  # type: ignore[arg-type]
            source="flag",
            reason="flag",
        )

    full_text = f"{title}\n{body}" if title else body

    # Step 2: Perspective
    fp_rate = first_person_rate(full_text)
    if fp_rate < FIRST_PERSON_RATE_MIN:
        return VoiceDecision(
            voice=VOICE_DEFAULT,
            source="auto",
            reason="third_person",
            perspective="third_person",
            first_person_rate=fp_rate,
            narrator_gender="unknown",
            evidence=None,
        )

    # Step 3: Reddit gender tag
    tag = find_narrator_tag(full_text)
    if tag is not None:
        gender, evidence = tag
        voice = decide_voice("first_person", gender)
        return VoiceDecision(
            voice=voice,  # type: ignore[arg-type]
            source="auto",
            reason="tag",
            perspective="first_person",
            first_person_rate=fp_rate,
            narrator_gender=gender,
            evidence=evidence,
        )

    # Step 4: LLM analysis
    prompt_template = load_prompt("voice.md")
    prompt_text = prompt_template.format(text=full_text)

    ans, _ = run_with_retries(
        backend,
        stage="voice",
        system=(
            "You are a narrative perspective and narrator identity analyzer. "
            "Output JSON strictly matching the schema."
        ),
        user=prompt_text,
        schema=VOICE_SCHEMA,
        validate=partial(validate_gender_answer, full_text),
        max_attempts=3,
    )

    if ans is not None and ans.get("narrator_gender") in {"female", "male"}:
        narrator_gender: Literal["female", "male", "unknown"] = ans["narrator_gender"]
        evidence_str: str | None = ans.get("evidence")
        reason: Literal["llm", "no_evidence"] = "llm"
    else:
        narrator_gender = "unknown"
        evidence_str = None
        reason = "no_evidence"

    # Step 5: Decide voice
    chosen_voice = decide_voice("first_person", narrator_gender)
    return VoiceDecision(
        voice=chosen_voice,  # type: ignore[arg-type]
        source="auto",
        reason=reason,
        perspective="first_person",
        first_person_rate=fp_rate,
        narrator_gender=narrator_gender,
        evidence=evidence_str,
    )
