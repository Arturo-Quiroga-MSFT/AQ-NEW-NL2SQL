from __future__ import annotations
import re
from typing import Iterable

COMMON_TYPO_MAP = {
    "cret": "create",
    "cretae": "create",
    "delte": "delete",
    "schma": "schema",
    "shema": "schema",
    "indx": "index",
    "colum": "column",
}
POLITENESS = re.compile(r"\b(please|can you|could you|would you|kindly)\b", re.I)
WHITESPACE = re.compile(r"\s+")

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
}


def collapse_whitespace(s: str) -> str:
    return WHITESPACE.sub(" ", s).strip()


def replace_number_words(tokens: Iterable[str]) -> list[str]:
    out = []
    for t in tokens:
        out.append(NUMBER_WORDS.get(t, t))
    return out


def correct_typos(tokens: list[str]) -> list[str]:
    return [COMMON_TYPO_MAP.get(t, t) for t in tokens]


def normalize(text: str) -> str:
    t = text.strip().lower()
    t = POLITENESS.sub("", t)
    t = t.replace(";", " ; ")  # keep separators spaced
    t = collapse_whitespace(t)
    tokens = t.split(" ")
    tokens = replace_number_words(tokens)
    tokens = correct_typos(tokens)
    return collapse_whitespace(" ".join(tokens))
