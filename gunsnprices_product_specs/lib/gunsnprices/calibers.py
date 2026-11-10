"""Recognize firearm calibers in product titles and normalize caliber fields.

The caliber list and the retailer spellings come from the GunsNPrices calibers dataset
(https://huggingface.co/datasets/gunsnprices/firearm-calibers). On top of the dataset spellings, common title forms are
generated: "300 Blackout", "12ga", "7.62 x 39", "45 Auto", "6.5 Creed", ".308 Winchester" and so on.
"""
from __future__ import annotations

import html
import itertools
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Dict, List, Optional, Tuple

__all__ = ["Caliber", "find_calibers", "find_caliber", "normalize_caliber", "list_calibers"]


@dataclass(frozen=True)
class Caliber:
    """A caliber (cartridge) from the GunsNPrices caliber list."""

    id: str        #: stable id, e.g. "9x19mmparabellum"
    name: str      #: display name, e.g. "9×19mm Parabellum"
    type: str      #: "handgun", "rifle", "rimfire", "shotgun", "airgun" or "muzzleloader"
    url: str = ""  #: GunsNPrices page comparing prices for this caliber ("" if none)


# word -> spellings used in titles. A word marked optional may be left out ("300 Blackout" for ".300 AAC Blackout").
_SYN = {
    "win": ["win", "winchester"], "winchester": ["winchester", "win"],
    "rem": ["rem", "remington"], "remington": ["remington", "rem"],
    "mag": ["mag", "magnum"], "magnum": ["magnum", "mag"],
    "wby": ["wby", "weatherby"], "weatherby": ["weatherby", "wby"],
    "spl": ["spl", "special"], "special": ["special", "spl"],
    "sprg": ["sprg", "springfield", "spfd"], "springfield": ["springfield", "sprg", "spfd"],
    "government": ["government", "govt", "gov"],
    "acp": ["acp", "auto"], "auto": ["auto", "acp"],
    "s&w": ["s&w", "s & w", "sw", "smith & wesson", "smith and wesson", "smith&wesson"],
    "blackout": ["blackout", "blk", "black out"],
    "creedmoor": ["creedmoor", "creed", "cm", "crd", "creedmore"],
    "parabellum": ["parabellum", "para", "luger"],
    "gauge": ["gauge", "ga", "gauges"],
    "bore": ["bore", "ga", "gauge"],
    "lr": ["lr", "long rifle"],
    "h&h": ["h&h", "h & h", "holland & holland", "holland and holland"],
    "h&r": ["h&r", "h & r"],
    "bm": ["bm", "bushmaster", "bush"],
}
_OPTIONAL = {"aac", "nato", "win", "winchester", "rem", "remington", "sprg", "springfield", "government"}
_SEP = r"[\s\-]*"


def _key(s: str) -> str:
    s = html.unescape(s or "").lower().replace("×", "x").replace("\u0445", "x")
    s = re.sub(r"(?<=\d)\.(?=\d)", "#", s)
    s = re.sub(r"[^a-z0-9#&]+", "", s)
    return s.replace("#", ".").replace("&", "and")


def _tokens(name: str) -> List[str]:
    s = html.unescape(name).lower().replace("×", "x")
    s = re.sub(r"^\.", "", s)
    return [t for t in re.split(r"\s+", s.strip()) if t]


def _token_alts(tok: str) -> List[str]:
    if re.fullmatch(r"\.?\d+(?:\.\d+)?x\d+mm[a-z]*", tok):           # 9x19mm, 5.56x45mm, 7.62x54mmr
        return [tok, re.sub(r"mm", "", tok)]
    if re.fullmatch(r"\d+mm", tok):
        return [tok, tok[:-2] + " mm"]
    alts = list(_SYN.get(tok, [tok]))
    if tok in _OPTIONAL:
        alts.append("")
    return alts


# common title spellings that the synonym table does not produce
_EXTRA = {
    ".300 AAC Blackout": ["300 aac", "300 bo", "300 black out", "300 blackout", "300 blk"],
    "6.5mm Creedmoor": ["6.5 creedmoor", "6.5 crd", "6.5 cm", "6.5mm cm", "6.5 cr"],
    "6mm Creedmoor": ["6 creedmoor"],
    ".22 LR": ["22lr", "22 lr", "22 long rifle"],
    ".22 WMR": ["22 mag", "22 magnum", "22 win mag", "22 wmr"],
    "5.56×45mm NATO": ["5.56 nato", "5.56mm nato", "556 nato", "5.56x45", "5.56", "5.56mm", "5.56 mm"],
    "7.62x51mm NATO": ["7.62 nato", "7.62mm nato", "762 nato", "762x51"],
    "7.62x39mm": ["762x39"],
    ".410 Bore": ["410 ga", "410 gauge", "410 bore"],
    ".45 Colt": ["45 lc", "45 long colt"],
    ".44 S&W Special": ["44 spl", "44 special", "44 spcl"],
    ".38 S&W Special": ["38 spl", "38 special", "38 spcl", "38 spc", "38 sp", "38 spp", "38+p"],
    ".357 Mag": ["357 rm", "357 rem mag", "357 rem magnum", "357 remington magnum", "357 remington mag"],
    "9×19mm Parabellum": ["9mm luger", "9mm para", "9 mm luger", "9mm"],
    "10mm Auto": ["10mm", "10 mm"],
    ".45 ACP": ["45 acp", "45 auto", "45 automatic", "45 automatic colt pistol"],
    ".40 S&W": ["40 s&w", "40 sw", "40 cal", "40s", ".40"],
    ".380 ACP": ["380 acp", "380 auto", "380"],
    ".243 Win": ["243", ".243"],
    ".308 Win": ["308", ".308"],
    ".350 Legend": [".350", "350 leg", "350 lgnd", "350 lgd"],
    ".450 BM": ["450 bushmaster", "450 bush"],
    ".204 Ruger": [".204"],
    ".177": ["177", ".177"],
    ".300 Win Mag": ["300 wm"],
    "7mm Remington Magnum": ["7mm rm", "7 rm", "7mm rem mag"],
    ".338 Lapua Mag": ["338 lapua", "338 lap"],
    ".30 Carbine": ["30 m1", "30 m1 carbine"],
    ".30-06 Springfield": ["30-06 sp"],
    "7.92×57mm Mauser": ["8x57", "8x57mm", "8x57 js", "8x57 is"],
    ".50 AE": ["50 action express"],
    "12 Gauge": ["12 ga", "12ga", "12 gauge", "12-gauge", "12g"],
    "20 Gauge": ["20 ga", "20ga", "20 gauge", "20-gauge", "20g"],
    "16 Gauge": ["16 ga", "16ga", "16 gauge", "16g"],
    "28 Gauge": ["28 ga", "28ga", "28 gauge", "28g"],
    "10 Gauge": ["10g"],
}
# a bare number or "Nmm" ("20", "307", "6.5mm") in a title is usually something else, not a caliber;
# the exceptions below were checked against GunsNPrices listings (right in 97%+ of cases)
_BARE = re.compile(r"^\.?\d+(?:\.\d+)?(?:\s*mm)?$")
_ALLOW_BARE = {"380", "410", "9mm", "10mm", "10 mm", "5.56", "5.56mm", "5.56 mm", "243", ".243", "308", ".308", ".40", ".350", ".204", "177", ".177"}
# "12g" next to CO2 is a 12-gram CO2 cartridge, not 12 gauge
_GRAM = re.compile(r"^\d+\s?g$")
# shotguns "O/U 12/28": gauge / barrel length; on ammo "20/25" is rounds per box / boxes per case; "20/28 gauge" is a two-gauge set
_CONTEXT = [
    (re.compile(r"(?<![a-z0-9./$#-])12/(?:1[89]|2\d|3[0-4])(?:\.5)?(?![\d/.])(?!\s*(?:ga|gauge|rd|round))"), "12gauge"),
    (re.compile(r"(?<![a-z0-9./$#-])20/(?:18|18\.5|2[0-46-9]|3[0-2])(?![\d/.])(?!\s*(?:ga|gauge|rd|round))"), "20gauge"),
    (re.compile(r"(?<![a-z0-9./$#-])28/(?:2[6-9]|3[0-2])(?![\d/.])(?!\s*(?:ga|gauge|rd|round))"), "28gauge"),
    (re.compile(r"(?<![a-z0-9.$#-])\.?357(?=\s*/\s*\.?38)"), "357mag"),                         # ".357/.38 Spl"
]


def _variants(name: str) -> List[str]:
    toks = _tokens(name)
    if not toks or "/" in name:
        return []
    out = set()
    for combo in itertools.islice(itertools.product(*[_token_alts(t) for t in toks]), 400):
        v = " ".join(x for x in combo if x)
        if v and (not _BARE.match(v) or v in _ALLOW_BARE):
            out.add(v)
    return sorted(out)


def _rx(variant: str) -> str:
    parts = []
    for i, tok in enumerate(variant.split(" ")):
        t = re.escape(tok)
        t = re.sub(r"(?<=\d)x(?=\d)", r"\\s*x\\s*", t)               # 7.62 x 39
        t = t.replace(r"\-", _SEP)                                   # 30-06 / 30 06
        parts.append(t)
    body = _SEP.join(parts)
    return r"\.?" + body if variant[:1].isdigit() else body


@lru_cache(maxsize=1)
def _index() -> Tuple[Dict[str, Caliber], "re.Pattern[str]", Dict[str, Caliber]]:
    raw = json.loads(resources.files(__package__).joinpath("data/calibers.json").read_text(encoding="utf-8"))["calibers"]
    by_key: Dict[str, Tuple[int, Caliber]] = {}
    by_id: Dict[str, Caliber] = {}
    conflict: Dict[str, List[Tuple[int, Caliber]]] = {}
    pats: Dict[str, str] = {}
    for c in raw:
        cal = by_id[c["id"]] = Caliber(c["id"], c["name"], c["type"], c.get("url") or "")
        names = [c["name"], c["site_name"]] + c["aliases"]
        extra = _EXTRA.get(c["name"], [])
        for n in names + extra:
            own = html.unescape(n).lower()
            for v in _variants(n) + ([own] if not _BARE.match(own) or own in _ALLOW_BARE else []):
                k = _key(v)
                if not k or not re.search(r"\d", k):
                    continue
                conflict.setdefault(k, [])
                if all(x[1].id != cal.id for x in conflict[k]):
                    conflict[k].append((c.get("n", 0), cal))
                pats.setdefault(k, _rx(v) if v != html.unescape(n).lower() or "/" not in v else re.escape(v))
    for k, cands in conflict.items():
        cands.sort(key=lambda x: -x[0])
        # one spelling, several calibers: keep the one with 10x+ more listings, otherwise the spelling is ambiguous
        if len(cands) == 1 or cands[0][0] >= 10 * max(1, cands[1][0]):
            by_key[k] = cands[0]
    keys = sorted(by_key, key=lambda k: -len(pats[k]))
    big = re.compile(r"(?<![a-z0-9.$])(?:" + "|".join(pats[k] for k in keys) + r")(?![a-z0-9])", re.I)
    return {k: v[1] for k, v in by_key.items()}, big, by_id


def _prep(text: str) -> str:
    s = html.unescape(text or "").lower().replace("×", "x").replace("”", '"').replace("″", '"')
    s = s.replace("®", "").replace("™", "")
    return re.sub(r"\s+", " ", s)


def find_calibers(text: str) -> List[Caliber]:
    """All calibers mentioned in ``text``, in order of appearance, without duplicates.

    >>> [c.name for c in find_calibers("Ruger GP100 .357 Mag / .38 Special 4.2in Revolver")]
    ['.357 Mag', '.38 S&W Special']
    """
    by_key, big, by_id = _index()
    s = _prep(text)
    co2 = "co2" in s
    hits = []
    for m in big.finditer(s):
        if co2 and _GRAM.match(m.group(0)):
            continue
        c = by_key.get(_key(m.group(0)))
        if c:
            hits.append((m.start(), c))
    for rx, cid in _CONTEXT:
        for m in rx.finditer(s):
            hits.append((m.start(), by_id[cid]))
    out, seen = [], set()
    for _, c in sorted(hits, key=lambda h: h[0]):
        if c.id not in seen:
            seen.add(c.id)
            out.append(c)
    return out


def find_caliber(text: str) -> Optional[Caliber]:
    """The first caliber mentioned in ``text``, or ``None``."""
    found = find_calibers(text)
    return found[0] if found else None


def normalize_caliber(value: str) -> Optional[Caliber]:
    """Normalize a caliber field ("9mm Luger", "5.56 NATO", "12 GA") to a :class:`Caliber`.

    The whole value is looked up first; if it isn't a known spelling, the first caliber found inside it is returned.
    """
    by_key, _, _ = _index()
    return by_key.get(_key(value)) or find_caliber(value)


def list_calibers() -> List[Caliber]:
    """The full caliber list."""
    _, _, by_id = _index()
    return sorted(by_id.values(), key=lambda c: c.name)
