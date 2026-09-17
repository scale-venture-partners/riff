"""Plain-text helpers shared by extractors and rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "u.s", "u.k",
    "inc", "ltd", "co", "corp", "no", "fig", "approx", "dept", "est", "vol", "al",
}
_SENTENCE_END = re.compile(r"([.!?]+)(['\")\]]*)(\s+)")
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
_INLINE_MD = [
    (re.compile(r"!\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\[[^\]]*\]"), r"\1"),
    (re.compile(r"`([^`]*)`"), r"\1"),
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),
    (re.compile(r"(?<!\w)(\*|_)(?!\s)(.+?)(?<!\s)\1(?!\w)"), r"\2"),
    (re.compile(r"<[^>]+>"), ""),
]


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    end: int

    @property
    def words(self) -> list[str]:
        return words(self.text)


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def split_sentences(text: str) -> list[Sentence]:
    """Split on terminal punctuation followed by whitespace, guarding common abbreviations and decimals."""
    out: list[Sentence] = []
    start = 0
    for m in _SENTENCE_END.finditer(text):
        end = m.end(2)
        before = text[start:m.start()]
        last = re.findall(r"[\w.]+$", before)
        token = last[0].lower().rstrip(".") if last else ""
        nxt = text[m.end() : m.end() + 1]
        if token in _ABBREVIATIONS or (len(token) == 1 and token.isalpha()):
            continue
        if m.group(1) == "." and nxt and nxt.islower():
            continue
        chunk = text[start:end].strip()
        if chunk:
            out.append(Sentence(chunk, start, end))
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(Sentence(tail, start, len(text)))
    return out


def strip_inline_markdown(text: str) -> str:
    for pattern, repl in _INLINE_MD:
        text = pattern.sub(repl, text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


def syllables(word: str) -> int:
    w = word.lower().strip("'’")
    if not w:
        return 0
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def flesch_kincaid_grade(text: str) -> float | None:
    sents = split_sentences(text)
    ws = words(text)
    if len(sents) < 3 or len(ws) < 30:
        return None
    syl = sum(syllables(w) for w in ws)
    return 0.39 * (len(ws) / len(sents)) + 11.8 * (syl / len(ws)) - 15.59
