"""Turn a tagged span of words into a value: people, rupees, minutes, stops.

The model finds where a detail is ("4 of us", "under 2k", "one and a half hours"); these
small deterministic parsers read the number out of it, so the arithmetic is never learned.
"""

from __future__ import annotations

import re

from .lexicon import NUMBER_WORDS

ONE = {"me", "myself", "alone", "solo"}
TWO = {"both", "couple", "date", "wife", "husband", "girlfriend", "boyfriend", "partner"}


def _number(word: str) -> float | None:
    w = word.casefold().replace(",", "")
    if re.fullmatch(r"\d+(\.\d+)?k", w):
        return float(w[:-1]) * 1000
    if re.fullmatch(r"\d+(\.\d+)?", w):
        return float(w)
    return NUMBER_WORDS.get(w)


def _first(words: list[str], skip=("a", "an")) -> float | None:
    for w in words:
        if w in skip:
            continue
        n = _number(w)
        if n is not None:
            return n
    return None


def people(words: list[str]) -> int | None:
    n = _first(words)
    if n is not None:
        return int(n)
    if set(words) & TWO:
        return 2
    if set(words) & ONE:
        return 1
    return None


def rupees(words: list[str]) -> int | None:
    for w in words:
        n = _number(w)
        if n is not None and n >= 10:
            return int(n)
    return None


def minutes(words: list[str]) -> int | None:
    text = " ".join(words)
    unit = 1 if re.search(r"\bminutes?\b", text) else 60
    if re.search(r"\b(one|1|an) and a half\b", text):
        return 90
    if re.search(r"\bcouple of\b", text):
        return 120
    if re.search(r"\bhalf an?\b", text) and not re.search(r"\d", text):
        return 30
    n = _first(words, skip=())
    if n is not None:
        return int(round(n * unit))
    return None


def stops(words: list[str]) -> int | None:
    n = _first(words)
    if n is not None:
        return int(n)
    return 1 if {"single", "one"} & set(words) else None
