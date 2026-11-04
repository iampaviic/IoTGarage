"""Normalise and validate Croatian plate text.

Format: CITY(2 letters) DIGITS(3-4) LETTERS(1-2)   e.g. ZG1234AB, ST555B
Printed as "ZG 1234-AB"; in messages and the database always without spaces/dash.

OCR often confuses similar shapes (O/0, I/1, B/8, S/5, Z/2, G/6). Because the
format says which positions are letters and which are digits, every
confusable character can be put back into the right class. Every such fix is
counted as a "substitution" and lowers the confidence of the reading.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

# official Croatian registration area codes (ASCII-folded: Č->C, Š->S, Ž->Z)
CITY_CODES = {
    "BJ", "BM", "CK", "DA", "DE", "DJ", "DU", "GS", "IM", "KA", "KC", "KR", "KT", "KZ", "MA", "NA",
    "NG", "OG", "OS", "PU", "PZ", "RI", "SB", "SK", "SL", "ST", "SI", "VK", "VT", "VU", "VZ", "ZD", "ZG", "ZU",
}

PLATE_RE = re.compile(r"^([A-Z]{2})(\d{3,4})([A-Z]{1,2})$")

# digit seen where a letter must be -> letter, and vice versa
TO_LETTER = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G", "7": "T", "8": "B"}
TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "U": "0", "I": "1", "L": "1", "J": "1", "T": "7",
            "Z": "2", "S": "5", "G": "6", "B": "8", "A": "4"}
# letters never used on Croatian plates
NOT_USED = {"Q": "O", "W": "V", "X": "K", "Y": "V"}

_FOLD = str.maketrans("ČĆŠŽĐčćšžđ", "CCSZDccszd")


# characters OCR typically invents for the shield or the plate border
SHIELD_JUNK = set("HBIl138|0OD")
BORDER_JUNK = set("I1L|J")
MAX_COST = 2.5


@dataclass(frozen=True)
class PlateCandidate:
    plate: str
    substitutions: int   # characters changed to fit the format
    trimmed: int         # junk characters removed (shield, border, dirt)
    known_city: bool
    trim_cost: float = 0.0

    @property
    def fix_cost(self) -> float:
        """How much the raw text had to be changed (0 = read exactly)."""
        return self.substitutions + self.trim_cost

    @property
    def cost(self) -> float:
        return self.fix_cost + (0 if self.known_city else 1.0)


def clean(raw: str) -> str:
    """Uppercase, fold diacritics, keep only A-Z and 0-9."""
    return re.sub(r"[^A-Z0-9]", "", raw.translate(_FOLD).upper())


def is_valid(plate: str, strict_city: bool = False) -> bool:
    m = PLATE_RE.match(plate)
    return bool(m) and (not strict_city or m.group(1) in CITY_CODES)


def format_plate(plate: str) -> str:
    m = PLATE_RE.match(plate)
    return "%s %s-%s" % m.groups() if m else plate


def _fit(chars: str, classes: Sequence[str]) -> Optional[tuple]:
    out, subs = [], 0
    for ch, cls in zip(chars, classes):
        if cls == "L":
            if ch.isalpha():
                if ch in NOT_USED:
                    ch, subs = NOT_USED[ch], subs + 1
                out.append(ch)
            elif ch in TO_LETTER:
                out.append(TO_LETTER[ch])
                subs += 1
            else:
                return None
        else:
            if ch.isdigit():
                out.append(ch)
            elif ch in TO_DIGIT:
                out.append(TO_DIGIT[ch])
                subs += 1
            else:
                return None
    return "".join(out), subs


def _trim_cost(text: str, drop: tuple) -> Optional[float]:
    """Cost of removing the characters at positions `drop`; None if not allowed.
    Allowed: one leading and one trailing character (border, dirt) and one
    character right after the city code (the shield)."""
    n = len(text)
    cost = 0.0
    interior = 0
    for i in drop:
        ch = text[i]
        if i == 0 or i == n - 1:
            cost += 0.5 if ch in BORDER_JUNK else 1.5
        elif i in (2, 3):
            interior += 1
            cost += 0.5 if ch in SHIELD_JUNK else 1.5
        else:
            return None
    if interior > 1:
        return None
    return cost


def candidates(raw: str, max_trim: int = 2) -> List[PlateCandidate]:
    """All format-valid interpretations of an OCR string, best (lowest cost) first."""
    text = clean(raw)
    found = {}
    if not 5 <= len(text) <= 8 + max_trim:
        return []
    n = len(text)
    drops = itertools.chain([()], *(itertools.combinations(range(n), k) for k in range(1, max_trim + 1)))
    for drop in drops:
        trim_cost = _trim_cost(text, drop)
        if trim_cost is None:
            continue
        core = "".join(c for i, c in enumerate(text) if i not in drop)
        for n_digits in (3, 4):
            n_letters = len(core) - 2 - n_digits
            if n_letters not in (1, 2):
                continue
            fitted = _fit(core, "LL" + "D" * n_digits + "L" * n_letters)
            if fitted is None:
                continue
            plate, subs = fitted
            cand = PlateCandidate(plate, subs, len(drop), plate[:2] in CITY_CODES, trim_cost)
            if cand.cost > MAX_COST:
                continue
            if plate not in found or cand.cost < found[plate].cost:
                found[plate] = cand
    return sorted(found.values(), key=lambda c: (c.cost, c.plate))


def best_candidate(raw: str) -> Optional[PlateCandidate]:
    c = candidates(raw)
    return c[0] if c else None


def normalize_many(raws: Iterable[str]) -> List[Optional[PlateCandidate]]:
    return [best_candidate(r) for r in raws]
