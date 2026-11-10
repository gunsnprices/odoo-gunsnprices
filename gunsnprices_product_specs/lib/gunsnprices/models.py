"""Identify the firearm model in a product title: brand -> family -> model.

The rules are GunsNPrices' hand-built model dictionaries (50 brands). They are the same rules that assign models to
listings on gunsnprices.com, so ``identify_model`` returns the same model names you see on the site.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Dict, List, Optional

__all__ = ["ModelMatch", "identify_model", "list_brands"]


@dataclass(frozen=True)
class ModelMatch:
    """Result of :func:`identify_model`."""

    brand: str                      #: brand as named on GunsNPrices, e.g. "Glock"
    family: str                     #: model family, e.g. "Glock 19"
    model: str                      #: most specific model, e.g. "Glock 19 Gen 5 MOS"
    generation: str = ""            #: "5", "V", "V3" ... or "" when unknown
    configs: List[str] = field(default_factory=list)   #: configurations found, e.g. ["MOS"], ["Compact"]
    features: List[str] = field(default_factory=list)  #: features found, e.g. ["Threaded Barrel", "FDE"]
    source: str = "title"           #: "title" or "mpn" (Glock part number decoded)


# airguns and airsoft are not firearms (the site filters them by category; here we go by the title)
_AIRGUN = re.compile(r"\bair\s*-?\s*(?:gun|rifle|pistol)s?\b|\bairgun|\bairsoft|\bbb\s*(?:gun|pistol|rifle)|\bpellets?\b|\bco2\b", re.I)

# accessories named after a gun ("Glock 19 holster", "Sig P365 XL 12rd Magazine", "Magpul PMAG for Glock 19"). A title that
# describes a gun (pistol/rifle/..., "15+1", a barrel length) or mentions the item as included ("w/ 3 magazines",
# "no magazine") is not an accessory. Checked against GunsNPrices firearm listings: 4 of 32,316 rejected by mistake.
_ACC_NOUN = re.compile(
    r"\b(?:holsters?|magazines?(?!\s*(?:pattern|compatible|well|release|disconnect|safety|catch|cut|tube|extension|fed)\b)|pmags?|slings?|"
    r"grip panels?|scope mounts?|recoil pads?|speed ?loaders?|mag(?:azine)? loaders?|cleaning kits?|pouch(?:es)?|snap caps?|replacement barrels?|"
    r"conversion kits?|parts kits?)\b")
_ACC_INCLUDED = re.compile(
    r"(?:(?:\bw/|\bwith\b|\bwithout\b|\bno\b|\band\b|&|\+|\bincl\w*|\bplus\b|\(\d\)|\b[1-9]\b|\btwo\b|\bthree\b|\bfour\b|,|\bor\b|\bextra\b|"
    r"\bspare\b|\bfactory\b|\bfits\b|\btakes\b|\baccepts\b|\buses\b)[^,]{0,14}|/\s*)$")
_GUN_WORDS = re.compile(
    r"\b(?:pistol|rifle|shotgun|revolver|handgun|carbine|firearm|semi-?auto(?:matic)?|bolt[- ]?action|pump|lever[- ]?action|single[- ]?shot|"
    r"o/u|over/under|sxs|sbr|derringer)\b|\d+\+1\b|\d+(?:\.\d+)?\s*-?\s*(?:\"|in\b|inch)")


def _is_accessory(title: str) -> bool:
    t = html.unescape(html.unescape(title)).lower()
    if _GUN_WORDS.search(t):
        return False
    return any(not _ACC_INCLUDED.search(t[max(0, m.start() - 16):m.start()]) for m in _ACC_NOUN.finditer(t))


_DASHES = str.maketrans({"‐": "-", "‑": "-", "–": "-", "—": "-", "“": '"', "”": '"', "’": "'",
                         "|": " | ", "*": " ", "®": "", "™": ""})


@lru_cache(maxsize=1)
def _data() -> List[dict]:
    raw = resources.files(__package__).joinpath("data/models.json").read_text(encoding="utf-8")
    dicts = json.loads(raw)["dicts"]
    for d in dicts:
        d["_rewrite"] = [(re.compile(k, re.I), v) for k, v in (d.get("title_rewrite") or {}).items()]
        d["_exclude"] = _any(d.get("exclude"))
        d["_exclude_soft"] = _any(d.get("exclude_soft"))
        d["_block"] = _any(d.get("other_brand_block"))
        d["_brand_any"] = re.compile(d["brand_rx"], re.I) if d.get("brand_rx") else re.compile(r"(?<![a-z])" + re.escape(d["brand_word"]) + r"(?![a-z])", re.I)
        d["_brand_start"] = re.compile(r"^\W*(?:" + d["brand_rx"] + ")", re.I) if d.get("brand_rx") else None
        d["_configs"] = [(k, re.compile(v, re.I)) for k, v in (d.get("configs") or {}).items()]
        d["_features"] = [(k, re.compile(v, re.I)) for k, v in (d.get("features") or {}).items()]
        d["_gens"] = [(k, re.compile(v, re.I)) for k, v in (d.get("gens") or {}).items()]
        d["_brand_names"] = {_key(x) for x in d.get("brand_names", [])}
        d["_deny_names"] = {_key(x) for x in d.get("deny_brand_names", [])}
        if d.get("mode") == "terms":
            for m in d["models"]:
                m["_match"] = re.compile(m["match"], re.I)
                m["_not"] = re.compile(m["not"], re.I) if m.get("not") else None
    return dicts


def _any(patterns: Optional[List[str]]):
    return re.compile("|".join(patterns), re.I) if patterns else None


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", html.unescape(s or "").lower())


def _norm(s: str, d: dict) -> str:
    s = html.unescape(s or "").translate(_DASHES)
    s = re.sub(r"\s+", " ", s.lower()).strip()
    for rx, to in d["_rewrite"]:
        s = rx.sub(to, s)
    return s


def list_brands() -> List[str]:
    """Brands covered by the model dictionaries."""
    return [d["brand"] for d in _data()]


# ---------- numeric mode (Glock): codes like 19, 19X, 43X, 20SF; generation from the title or the part number ----------
def _find_models(t: str, d: dict) -> List[dict]:
    bw = re.escape(d["brand_word"])
    rx = re.compile(r"(?<![a-z0-9.])(?:" + bw + r"\s*-?\s*g?\s*-?\s*|g)(\d{2})(?:(sf|x|c|l|m|s)|\s(sf|x)(?![a-z0-9]))?(?:g([1-6])(?:us)?|(v))?(fs|mos|rtf)?"
                    r"(?![a-z0-9&\"+/])(?!\s*-?\s*(?:round|rounds|rd|rds|rnd|mag|mags|magazine)\b)", re.I)
    found = []
    for m in rx.finditer(t):
        num = m.group(1).lower()
        suf = (m.group(2) or m.group(3) or "").upper()
        code = num + suf if num + suf in d["models"] else (num if num in d["models"] else "")
        if not code:
            continue
        found.append({"code": code, "num": num, "pos": m.start(), "end": m.end(), "mos": (m.group(6) or "").lower() == "mos",
                      "gen": m.group(4) or ("V" if m.group(5) else "")})
    return found


def _decode_mpn(name: str, mpn: str, sku: str, d: dict) -> Optional[dict]:
    cands = [mpn or "", sku or ""]
    cands += re.findall(r"\b(?:gl)?[pue][a-z0-9]\d{3}[a-z0-9-]*|\bg\d{2}c?\d{3}us\b|\bg\d{4}[a-z]*aut\b", name or "", re.I)
    for c in cands:
        c = c.strip()
        m = re.match(r"^G(\d{2}C?)([345])(\d{2})US$", c, re.I)
        if m and m.group(1).upper() in d["models"]:
            return {"code": m.group(1).upper(), "letter": "", "mpn": c, "gen": m.group(2)}
        m = re.match(r"^G(\d{2})\d{2}[A-Z]*AUT$", c, re.I)
        if m and m.group(1) in d["models"]:
            return {"code": m.group(1), "letter": "", "mpn": c, "gen": ""}
        m = re.match(r"^(?:GL)?([PUE])([A-Z0-9])(\d{2})(\d)", c, re.I)
        if not m:
            continue
        letter, num = m.group(2).upper(), m.group(3)
        num = (d.get("mpn_model_alias") or {}).get(num, num)
        code = (d.get("mpn_letter_model") or {}).get(letter + num, num)
        if code not in d["models"]:
            continue
        return {"code": code, "letter": letter, "mpn": c, "gen": (d.get("mpn_letter_gen") or {}).get(letter, "")}
    return None


def _parse_numeric(t: str, name: str, brand: Optional[str], mpn: str, sku: str, d: dict) -> Optional[dict]:
    pm = _decode_mpn(name, mpn, sku, d)
    if not pm and d["_exclude_soft"] and d["_exclude_soft"].search(t):
        return None
    if brand:
        own = _key(brand) in d["_brand_names"] or bool(pm)
    else:
        own = bool(pm) or bool(re.match(r"^\W*" + re.escape(d["brand_word"]) + r"\b", t, re.I))
    models = _find_models(t, d)
    if not models and own:
        m = re.match(r"^(\d{2})(x)?\b", t)
        if m and m.group(1) + (m.group(2) or "").upper() in d["models"]:
            code = m.group(1) + (m.group(2) or "").upper()
            models = [{"code": code, "num": m.group(1), "pos": 0, "end": m.end(), "mos": False, "gen": ""}]
    if not models and own and d.get("bare_model_tokens"):
        m = re.search(r"\b(" + "|".join(d["bare_model_tokens"]) + r")\b", t)
        if m:
            models = [{"code": m.group(1).upper(), "num": m.group(1)[:2], "pos": m.start(), "end": m.end(), "mos": False, "gen": ""}]
    if not own:
        if not models:
            return None
        if d["_block"] and d["_block"].search(t):
            return None
    src = "title"
    first = None
    if models:
        first = models[0]
        code = first["code"]
        for x in models:
            if x["num"] == first["num"] and len(x["code"]) > len(code):
                code = x["code"]
    elif own and pm:
        code, src = pm["code"], "mpn"
    else:
        return None
    gen = ""
    if first and first["gen"]:
        gen = first["gen"]
    else:
        m = re.search(r"\bgen(?:eration)?\.?\s*-?\s*([1-6])\b|\b([1-6])(?:st|nd|rd|th)\s*gen\b|\bg([1-6])\b", t)
        if m:
            gen = m.group(1) or m.group(2) or m.group(3)
        elif first and re.match(r"^\s*v\b", t[first["end"]:]):
            gen = "V"
        elif pm and pm["gen"] and pm["code"] == code:
            gen = pm["gen"]
    if code in (d.get("no_gen_models") or []) and gen != "V":
        gen = ""
    configs = [n for n, rx in d["_configs"]
               if rx.search(t) or (n == "MOS" and ((first and first["mos"]) or (pm and "mos" in pm["mpn"].lower())))]
    features = [n for n, rx in d["_features"] if rx.search(t)]
    if pm and re.search(r"\d(?:mos)?tb\b", pm["mpn"], re.I) and "Threaded Barrel" not in features:
        features.append("Threaded Barrel")
    return {"code": code, "family": d["models"][code], "gen": gen, "configs": configs, "features": features, "src": src}


# ---------- terms mode (all other brands): ordered list of model patterns, first match wins ----------
def _parse_terms(t: str, brand: Optional[str], d: dict) -> Optional[dict]:
    if brand and _key(brand) in d["_deny_names"]:
        return None
    own = (bool(brand) and _key(brand) in d["_brand_names"]) or bool(d["_brand_start"].search(t))
    if not own:
        if not d["_brand_any"].search(t):
            return None
        if d["_block"] and d["_block"].search(t):
            return None
    hit = None
    for m in d["models"]:
        if m["_match"].search(t) and not (m["_not"] and m["_not"].search(t)):
            hit = m
            break
    if not hit:
        return None
    allowed = d.get("other_brand_models")
    if not own and allowed and hit["name"] not in allowed:
        return None
    gen = next((label for label, rx in d["_gens"] if rx.search(t)), "")
    configs = []
    implied = d.get("config_implied_by_gen_family") or {}
    for name, rx in d["_configs"]:
        if name not in (hit.get("configs") or []):
            continue
        imp = (implied.get(name) or {}).get(hit["family"], [])
        if rx.search(t) or (gen and gen in imp) or name in (hit.get("implied_configs") or []):
            configs.append(name)
    features = [n for n, rx in d["_features"] if rx.search(t)]
    return {"code": hit["name"], "family": hit["family"], "gen": gen, "configs": configs, "features": features, "src": "title"}


def _rank(title: str, d: dict, brand: Optional[str]):
    """Which matching dictionary wins: the product's own brand -> brand at the start of the title -> brand mentioned earlier."""
    if brand and _key(brand) in d["_brand_names"]:
        return (0, 0)
    t = _norm(title, d)
    m = d["_brand_any"].search(t)
    if m and m.start() <= 2:
        return (1, 0)
    return (2, m.start() if m else 10 ** 6)


def _leaf(r: dict, d: dict) -> str:
    if d.get("mode") == "terms":
        s = r["code"] + (" " + r["gen"] if r["gen"] else "")
    else:
        s = d["brand"] + " " + r["code"]
        if r["gen"]:
            s += " V" if r["gen"] == "V" else " Gen " + r["gen"]
    for c in r["configs"]:
        # skip a config already spelled out in the name ("Plus Shield" on "S&W M&P Shield Plus")
        if not re.search(r"(?<![a-z0-9])" + re.escape(c) + r"(?![a-z0-9])", s, re.I) \
                and not set(re.findall(r"[a-z0-9.&+]+", c.lower())) <= set(re.findall(r"[a-z0-9.&+]+", s.lower())):
            s += " " + c
    needed = (d.get("needed") or {}).get(r["family"], [])
    for f in d.get("feature_order", []):
        if f in r["features"] and f in needed:
            s += " " + f
    return s


def _parse_one(title: str, d: dict, brand: Optional[str], mpn: str, sku: str) -> Optional[dict]:
    t = _norm(title, d)
    if d["_exclude"] and d["_exclude"].search(t):
        return None
    if d.get("mode") == "terms":
        return _parse_terms(t, brand, d)
    # the numeric dictionary (Glock) only runs when the brand is given or named in the title;
    # otherwise part-number decoding picks up other brands' codes (CVA "PR3110S" -> "Glock 31")
    if not ((brand and _key(brand) in d["_brand_names"]) or d["_brand_any"].search(t)):
        return None
    return _parse_numeric(t, title, brand, mpn, sku, d)


def identify_model(title: str, brand: Optional[str] = None, mpn: str = "", sku: str = "") -> Optional[ModelMatch]:
    """Find the brand, model family and model in a firearm product title.

    :param title: product title as a store shows it, e.g. ``"Glock 19 Gen 5 MOS 9mm 4.02in 15rd Pistol PA195S203MOS"``
    :param brand: the manufacturer if you know it (helps with titles that don't name the brand)
    :param mpn: manufacturer part number, if known (Glock part numbers encode the model and generation)
    :param sku: store SKU, if known
    :returns: :class:`ModelMatch` or ``None`` when no covered brand/model is recognized.

    Only firearms are covered: titles of accessories, parts and airguns return ``None``.
    """
    if not title or _AIRGUN.search(title) or _is_accessory(title):
        return None
    hits = []
    for d in _data():
        r = _parse_one(title, d, brand, mpn, sku)
        if r:
            hits.append((_rank(title, d, brand), d, r))
    if not hits:
        return None
    hits.sort(key=lambda x: x[0])
    _, d, r = hits[0]
    fam = (d.get("family_display") or {}).get(r["family"]) or (d["brand"] + " " + r["family"] if d.get("mode") != "terms" else r["family"])
    return ModelMatch(brand=d["brand"], family=fam, model=_leaf(r, d), generation=r["gen"], configs=list(r["configs"]),
                      features=list(r["features"]), source=r["src"])
