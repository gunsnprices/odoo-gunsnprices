"""Numbers from product titles: magazine capacity, barrel length, rounds per box and cost per round."""
from __future__ import annotations

import html
import re
from typing import Optional

__all__ = ["magazine_capacity", "barrel_length", "rounds_per_box", "cost_per_round", "looks_like_ammo"]


def _prep(text: str) -> str:
    s = html.unescape(html.unescape(text or "")).lower()
    s = s.replace("”", '"').replace("″", '"').replace("“", '"').replace("''", '"').replace("’’", '"')
    s = s.replace("®", "").replace("™", "")
    return re.sub(r"\s+", " ", s)


_NUM = r"(\d{1,3}(?:,\d{3})+|\d{1,5})"
_AMMO = re.compile(
    r"\b(?:ammo|ammunition|shotshells?|shot ?shells?|cartridges?|bullets?|primers?|slugs?|buckshot|pellets?|bbs?|grains?|\d+\s*gr|"
    r"per box|box of|rounds? box|rds?/box)\b|/\s*(?:box|bx|pk|pack|case|cs|tin)\b"
)


def looks_like_ammo(title: str) -> bool:
    """True if the title reads like ammunition (bullet weight, "ammo", "20/box", ...) rather than a firearm."""
    return bool(_AMMO.search(_prep(title)))


# --- magazine capacity --------------------------------------------------------------------------------------------------

_CAP_PLUS = re.compile(r"(?<![\d.:/x])(\d{1,3})\s*\+\s*1(?!\d)")                                 # 15+1
_CAP_RD = re.compile(r"(?<![\d.:/x])(\d{1,3})\s*-?\s*(?:rd|rds|rnd|rnds|round|rounds|shot|shots)\b(?!\s*/?\s*(?:per\b|box|bx|pack|pk|case))")
# "13rd/15rd", "1-30Rd/1-10Rd Mag": ships with magazines of two sizes - take the larger one
_CAP_PAIR = re.compile(r"(?<![\d.:/x])(\d{1,3})\s*-?\s*(?:rd|rds|rnd|rnds|rounds?)?\s*/\s*(?:1?-)?(\d{1,3})\s*-?\s*(?:rd|rds|rnd|rnds|rounds?)\b")
_CAP_MAG = re.compile(r"\b(?:cap|capacity)\s*[:=]?\s*(\d{1,3})\b(?!\s*(?:\"|in\b|gr\b))")


def magazine_capacity(title: str) -> Optional[int]:
    """Magazine capacity of a firearm or magazine from its title ("17RD", "15+1", "10-shot"), or ``None``.

    For "15+1" the magazine capacity (15) is returned. Use it on firearm and magazine titles: in ammunition titles
    "20 rounds" means rounds per box (see :func:`rounds_per_box`).

    >>> magazine_capacity("Glock 19 Gen5 9mm 4.02in 15+1 Black")
    15
    """
    s = _prep(title)
    m = _CAP_PAIR.search(s)
    if m and 1 <= max(int(m.group(1)), int(m.group(2))) <= 110:
        return max(int(m.group(1)), int(m.group(2)))
    for rx in (_CAP_PLUS, _CAP_RD, _CAP_MAG):
        for m in rx.finditer(s):
            n = int(m.group(1))
            if 1 <= n <= 110:
                return n
    return None


# --- barrel length ------------------------------------------------------------------------------------------------------

_INCH = r'(?:"|in\b(?!\s*(?:1\b|stock\b|one\b))\.?|inch(?:es)?\b|-inch\b|-in\b)'
_LEN = r"(\d{1,2}(?:\.\d{1,3})?)(?:[\s-]+(\d{1,2})/(\d{1,2}))?"                                            # 18.5 / 16 1/2
_BBL = r"(?:bbl|brl|barrel)\b"
_BAR_TAGGED = [
    re.compile(r"(?<![\d.:/x#$-])" + _LEN + r"\s*-?\s*" + _INCH + r"?\s*" + _BBL),                         # 20" barrel, 22 bbl
    re.compile(r"\b(?:bbl|brl|barrel)\s*(?:length)?\s*[:=]?\s*" + _LEN + r"\s*" + _INCH),              # barrel: 20"
]
_BAR_INCH = re.compile(r"(?<![\d.:/x#$-])" + _LEN + r"\s*-?\s*" + _INCH)
_NOT_BARREL_AFTER = re.compile(r"\s*-?\s*(?:chamber|chbr|chmbr|shells?|m-?lok|mlok|handguard|hg\b|rail|keymod|quad|lop\b|length of pull|oal\b|twist|rate)")
_NOT_BARREL_BEFORE = re.compile(r"(?:lop|oal|overall|length of pull|pull|twist|1:|chamber|m-?lok|mlok|handguard|rail|sight radius)\s*[:=]?\s*$")
_SHOTGUN = re.compile(r"\b(?:\d{1,2}|410)\s*(?:ga|gauge|g)\b|\.410|shotgun|o/u|over/under|sxs|side by side|\b(?:12|16|20|28|410)/\d\d\b")
# "O/U 12/28": gauge / barrel length (10 is left out: "10/22" is a Ruger rifle)
_GAUGE_SLASH = re.compile(r"(?<![a-z0-9./$#-])(?:12|16|20|28|410)/(1[89](?:\.5)?|2\d|3[0-4])(?![\d/.])(?!\s*(?:ga|gauge|rd|round))")


def _length(m: "re.Match[str]") -> float:
    v = float(m.group(1))
    if m.group(2) and m.group(3) and int(m.group(3)) in (2, 4, 8, 16) and int(m.group(2)) < int(m.group(3)):
        v += int(m.group(2)) / int(m.group(3))
    return v


def barrel_length(title: str) -> Optional[float]:
    """Barrel length in inches from a firearm title ('4.25"', "16 in", "20-inch", '16 1/2"', "22 BBL"), or ``None``.

    Chamber length (3" on shotguns), twist rate, handguard and length-of-pull values are skipped.

    >>> barrel_length('Ruger GP100 .357 Mag 4.2in Revolver')
    4.2
    """
    s = _prep(title)
    for rx in _BAR_TAGGED:
        for m in rx.finditer(s):
            v = _length(m)
            if 1.5 <= v <= 36:
                return v
    m = _GAUGE_SLASH.search(s)
    if m:
        return float(m.group(1))
    shotgun = bool(_SHOTGUN.search(s))
    for m in _BAR_INCH.finditer(s):
        v = _length(m)
        if not 1.5 <= v <= 36:
            continue
        if _NOT_BARREL_AFTER.match(s, m.end()) or _NOT_BARREL_BEFORE.search(s[max(0, m.start() - 20):m.start()]):
            continue
        if shotgun and v <= 3.5:                                                                           # 3" chamber
            continue
        return v
    return None


# --- rounds per box -----------------------------------------------------------------------------------------------------

_B = r"(?<![a-z0-9.#$/])"
_RPB = [
    re.compile(_B + _NUM + r"\s*-?\s*(?:rd|rds|round|rounds|rnd|rnds|ct|count|pcs|pc|cartridges|shells|shotshells|bullets)\b(?!\s*(?:mag|magazine|capacity|cap)\b)"),
    re.compile(_B + _NUM + r"\s*(?:/\s*|per\s+)(?:box|bx|pack|pk|case|cs|tin|can|bag|ct)\b"),
    re.compile(r"(?:box|pack|case|tin|bx|bag|can) of\s*" + _NUM),
    re.compile(_B + _NUM + r"\s*-?\s*(?:pack|pk|packs)\b"),
]
# distributor notation "50/10", "20/25": rounds per box / boxes per case
_BOX_CASE = re.compile(r"(?<![\d.\-/])(5|10|15|18|20|25|30|40|50|100|200|250|500|1000)\s*/\s*(\d{1,3})(?![\d/.\"])")
_CALIBER_SLASH = {("30", "30"), ("45", "70"), ("30", "06"), ("22", "250"), ("25", "06"), ("38", "55"), ("44", "40"), ("32", "20"), ("38", "40"), ("25", "20"), ("32", "40")}


def rounds_per_box(title: str) -> Optional[int]:
    """Number of rounds in one package of ammunition ("20rds", "50/box", "Box of 25", "1,000 Rounds"), or ``None``.

    >>> rounds_per_box("Federal American Eagle 9mm 115gr FMJ, 50/Box")
    50
    """
    s = _prep(title)
    for rx in _RPB:
        m = rx.search(s)
        if m:
            n = int(m.group(1).replace(",", ""))
            if 1 <= n <= 20000:
                return n
    for m in _BOX_CASE.finditer(s):
        if (m.group(1), m.group(2)) not in _CALIBER_SLASH and m.group(2) not in ("2", "4", "8", "16", "32"):
            return int(m.group(1))
    return None


def cost_per_round(price: float, rounds: Optional[int]) -> Optional[float]:
    """Price of one round, rounded to 4 decimals (``None`` without a price or a round count).

    >>> cost_per_round(18.99, 50)
    0.3798
    """
    if not price or not rounds or price <= 0 or rounds <= 0:
        return None
    return round(price / rounds, 4)
