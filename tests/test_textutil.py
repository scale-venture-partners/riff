"""Unit tests for the text helpers. Exact assertions, to pin arithmetic and regex behavior
(these kill mutation-testing survivors that loose assertions would miss)."""

from __future__ import annotations

from riff.textutil import (
    estimate_tokens,
    flesch_kincaid_grade,
    split_sentences,
    syllables,
    word_count,
    words,
)


def test_split_sentences_count_and_text():
    s = split_sentences("First sentence here. Second one follows! A third? Yes indeed.")
    assert [x.text for x in s] == ["First sentence here.", "Second one follows!", "A third?", "Yes indeed."]


def test_split_sentences_guards_abbreviations_and_decimals():
    s = split_sentences("Dr. Smith paid $3.50 for it. Then he left.")
    assert len(s) == 2


def test_split_sentences_guards_single_letter_initial():
    # "A." must not end a sentence (single-letter initial guard).
    assert len(split_sentences("Written by A. Turing today. It shipped.")) == 2


def test_word_count_and_words():
    assert word_count("one two three") == 3
    assert words("it's a test-case") == ["it's", "a", "test-case"]


def test_syllables_exact():
    # 'cakes'/'hoped' exercise the trailing es/ed/e stripping; a broken regex there changes the count.
    assert syllables("cat") == 1
    assert syllables("writing") == 2
    assert syllables("cakes") == 1
    assert syllables("hoped") == 1
    assert syllables("area") == 2
    assert syllables("calibration") == 4
    assert syllables("") == 0
    assert syllables("'") == 0


def test_flesch_none_when_too_few_words_despite_enough_sentences():
    # Four sentences but under 30 words: must return None. Distinguishes `or` from `and` in the guard.
    short = "A cat sat here. A dog ran fast. A bird flew away. A fish swam by."
    assert len(split_sentences(short)) >= 3
    assert word_count(short) < 30
    assert flesch_kincaid_grade(short) is None


def test_flesch_none_when_too_short():
    assert flesch_kincaid_grade("Too short.") is None


def test_flesch_exact_value():
    text = (
        "The committee reviewed the comprehensive proposal very carefully before lunch. "
        "Members discussed the significant financial implications thoroughly among themselves. "
        "They ultimately postponed the rather difficult decision until the following fiscal quarter finally began."
    )
    grade = flesch_kincaid_grade(text)
    assert grade is not None
    assert abs(grade - 16.59) < 0.1   # pins the coefficients and operators


def test_estimate_tokens_exact_int():
    v = estimate_tokens("a" * 400)
    assert v == 101                    # 400 // 4 + 1, integer division
    assert isinstance(v, int)
    assert estimate_tokens("") == 1
