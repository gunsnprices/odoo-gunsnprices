"""Turn a product name into spec values and decide which fields to write.

No Odoo imports: the model in models/product_template.py feeds records in, and the same code is unit-tested without
an Odoo server (tests/ at the repository root).

Spec keys used here (the model maps them to its gnp_* fields):

    kind               "firearm" or "ammo"
    brand              brand of the recognized model ("Glock")
    model_family       "Glock 19"
    model              "Glock 19 Gen 5 MOS"
    generation         "5", "V", "V3" ...
    caliber            caliber code of the first caliber in the name ("9x19mmparabellum")
    other_calibers     tuple of codes of the other calibers in the name (".357 Mag / .38 Special")
    magazine_capacity  int
    barrel_length      float, inches
    rounds_per_box     int
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from .parser import gnp

__all__ = ["SPEC_KEYS", "parse_product", "plan_update", "fill_records", "cost_per_round", "is_true"]

SPEC_KEYS = (
    "kind", "brand", "model_family", "model", "generation", "caliber", "other_calibers",
    "magazine_capacity", "barrel_length", "rounds_per_box",
)


def is_true(value) -> bool:
    """Value of a boolean system parameter ("True", "1", "yes" ...)."""
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def cost_per_round(price: float, rounds: int | None) -> float:
    """Price of one round (4 decimals), 0.0 without a price or a round count."""
    return gnp.cost_per_round(price, rounds) or 0.0


def parse_product(name: str, brand: str = "", reference: str = "", kind: str = "") -> dict[str, object]:
    """Specs found in a product name. Only what was found is returned; an empty dict means nothing was recognized.

    :param name: product name
    :param brand: brand already known for the product; helps when the name doesn't start with it
    :param reference: internal reference / SKU / MPN (Glock part numbers give model and generation)
    :param kind: "firearm" or "ammo" if already known, else guessed from the name

    "kind" is only returned when the name was not given a kind and it is clear: "ammo" for a name that reads like
    ammunition and has a caliber or a round count, "firearm" when a model from the dictionaries is recognized.
    Names of accessories, parts and airguns don't get a model (a magazine still gets its caliber and capacity).
    """
    known_kind = kind if kind in ("firearm", "ammo") else None
    info = gnp.parse_title(name or "", brand=brand or None, mpn=reference or "", kind=known_kind)
    found: dict[str, object] = {}
    if info.model:
        found.update(brand=info.model.brand, model_family=info.model.family, model=info.model.model)
        if info.model.generation:
            found["generation"] = info.model.generation
    if info.calibers:
        found["caliber"] = info.calibers[0].id
        if len(info.calibers) > 1:
            found["other_calibers"] = tuple(c.id for c in info.calibers[1:])
    if info.capacity:
        found["magazine_capacity"] = info.capacity
    if info.barrel_length:
        found["barrel_length"] = info.barrel_length
    if info.rounds:
        found["rounds_per_box"] = info.rounds
    if not known_kind:
        if info.kind == "ammo" and (info.rounds or info.calibers):
            found["kind"] = "ammo"
        elif info.kind == "firearm" and info.model:
            found["kind"] = "firearm"
    return found


def _empty(value) -> bool:
    return value is None or value is False or value == "" or value == 0 or value == ()


def _same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-6
        except (TypeError, ValueError):
            return False
    if isinstance(a, (tuple, list)) or isinstance(b, (tuple, list)):
        return set(a or ()) == set(b or ())
    return a == b


def plan_update(current: dict[str, object], found: dict[str, object], overwrite: bool = False) -> dict[str, object]:
    """Values to write: found values for empty fields, or for every field with ``overwrite``.

    A field is never cleared: when nothing was found for it, it keeps its value even with ``overwrite``.
    Values equal to the current ones are left out, so an empty result means "nothing to change".
    """
    changes: dict[str, object] = {}
    for key, value in found.items():
        if key in ("caliber", "other_calibers") or _empty(value):
            continue
        cur = current.get(key)
        if (overwrite or _empty(cur)) and not _same(cur, value):
            changes[key] = value
    if found.get("caliber"):
        cur_main = current.get("caliber") or ""
        main = found["caliber"] if (overwrite or not cur_main) else cur_main
        if main != cur_main:
            changes["caliber"] = main
        # every caliber in the name except the one kept as the main caliber
        others = tuple(c for c in (found["caliber"],) + tuple(found.get("other_calibers") or ()) if c != main)
        cur_others = tuple(current.get("other_calibers") or ())
        if others and (overwrite or not cur_others) and not _same(others, cur_others):
            changes["other_calibers"] = others
    return changes


def fill_records(records: Iterable, overwrite: bool = False, write: Callable | None = None) -> dict[str, int]:
    """Fill specs on records and count what happened.

    Each record provides ``_gnp_specs_input()`` (dict: name, brand, reference, kind), ``_gnp_current_specs()``
    (dict of the spec keys) and ``_gnp_write_specs(changes)``; ``write(record, changes)`` replaces the last one.

    :returns: {"updated": n, "unchanged": n, "not_found": n}
    """
    stats = {"updated": 0, "unchanged": 0, "not_found": 0}
    for rec in records:
        found = parse_product(**rec._gnp_specs_input())
        if not found:
            stats["not_found"] += 1
            continue
        changes = plan_update(rec._gnp_current_specs(), found, overwrite)
        if not changes:
            stats["unchanged"] += 1
            continue
        if write:
            write(rec, changes)
        else:
            rec._gnp_write_specs(changes)
        stats["updated"] += 1
    return stats
