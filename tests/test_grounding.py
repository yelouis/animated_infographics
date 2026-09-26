"""Unit tests for grounding, number extraction, and verbatim span validation."""

from animated_infographics.planner.grounding import (
    digits_grounded,
    is_kinetic_quote_grounded,
    is_stat_grounded,
    is_verbatim_span,
    numbers,
)


def test_numbers_digit_with_scale() -> None:
    nums = numbers("2.3 million gallons of molasses")
    assert 2.3 in nums
    assert 2.3e6 in nums


def test_grounding_scale_words() -> None:
    """Verify scale words are not numbers on their own."""
    nums_holding = numbers("holding 2.3 million gallons")
    assert 2.3 in nums_holding
    assert 2300000.0 in nums_holding
    assert 1000000.0 not in nums_holding

    nums_a_million = numbers("a million reasons")
    assert 1000000.0 in nums_a_million

    nums_two_million = numbers("two million")
    assert 2000000.0 in nums_two_million


def test_numbers_spelled_twenty_one() -> None:
    nums = numbers("Twenty-one people died in the flood.")
    assert 21.0 in nums


def test_numbers_currency_and_commas() -> None:
    nums = numbers("The repairs cost $1,500 in total.")
    assert 1500.0 in nums


def test_numbers_spelled_a_thousand() -> None:
    nums = numbers("They walked a thousand miles.")
    assert 1000.0 in nums


def test_stat_1500_rejected_against_150_injured() -> None:
    beat_text = "about 150 were injured in the disaster"
    # value=1500 is rejected
    assert not is_stat_grounded(1500.0, "none", beat_text)
    # value=150 is accepted
    assert is_stat_grounded(150.0, "none", beat_text)


def test_stat_scale_combinations() -> None:
    beat_text = "The company produced 2.3 million units."
    # 2.3 million matches
    assert is_stat_grounded(2.3, "million", beat_text)
    assert is_stat_grounded(2300000.0, "none", beat_text)
    # 23 million is rejected
    assert not is_stat_grounded(23.0, "million", beat_text)


def test_verbatim_span_rejects_paraphrase_and_mid_word() -> None:
    haystack = "The Great Molasses Flood was an unusual disaster in Boston."

    # Exact match works
    assert is_verbatim_span("The Great Molasses Flood", haystack)
    assert is_verbatim_span("unusual disaster", haystack)

    # Paraphrase is rejected
    assert not is_verbatim_span("A huge molasses wave", haystack)

    # Mid-word start is rejected ("olasses" from "Molasses")
    assert not is_verbatim_span("olasses", haystack)
    # Mid-word end is rejected ("disaste" from "disaster")
    assert not is_verbatim_span("unusual disaste", haystack)


def test_digits_grounded() -> None:
    transcript = "In 1919, twenty-one people lost their lives and 150 were injured."

    # Literal digits present
    assert digits_grounded("1919", transcript)
    assert digits_grounded("150", transcript)

    # Digits from spelled number "twenty-one"
    assert digits_grounded("21", transcript)

    # Date label with mixed text and grounded digits
    assert digits_grounded("Jan 1919", transcript)

    # Ungrounded digits
    assert not digits_grounded("1920", transcript)
    assert not digits_grounded("1500", transcript)


def test_kinetic_quote_grounding() -> None:
    beat_text = "The giant tank gave way with a tremendous roar."

    # Valid quote with ellipsis and emphasis
    valid, errors = is_kinetic_quote_grounded(
        "The giant tank gave way…", ["giant", "tank"], beat_text
    )
    assert valid
    assert len(errors) == 0

    # Invalid quote (words not in beat)
    valid, errors = is_kinetic_quote_grounded("A huge metal container exploded", [], beat_text)
    assert not valid
    assert any("not a verbatim span" in e for e in errors)

    # Invalid emphasis (word not in quote text)
    valid, errors = is_kinetic_quote_grounded("The giant tank gave way", ["tremendous"], beat_text)
    assert not valid
    assert any("not a whole word" in e for e in errors)
