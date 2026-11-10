"""One call for everything: parse a firearm or ammunition product title."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional

from .calibers import Caliber, find_calibers
from .models import ModelMatch, identify_model
from .specs import barrel_length, cost_per_round, looks_like_ammo, magazine_capacity, rounds_per_box

__all__ = ["ProductInfo", "parse_title"]


@dataclass(frozen=True)
class ProductInfo:
    """Result of :func:`parse_title`. Fields that don't apply or weren't found are ``None`` (or empty)."""

    title: str
    kind: str                                   #: "firearm" or "ammo"
    brand: str = ""                             #: brand of the identified model, else the ``brand`` argument, else ""
    model: Optional[ModelMatch] = None          #: firearms only
    caliber: Optional[Caliber] = None           #: first caliber in the title
    calibers: List[Caliber] = field(default_factory=list)   #: every caliber in the title ("357 Mag / 38 Special")
    capacity: Optional[int] = None              #: magazine capacity, firearms only
    barrel_length: Optional[float] = None       #: inches, firearms only
    rounds: Optional[int] = None                #: rounds per box, ammo only
    cost_per_round: Optional[float] = None      #: ammo only, needs ``price``

    def to_dict(self) -> dict:
        """Plain dict (JSON-serializable)."""
        return asdict(self)


def parse_title(title: str, brand: Optional[str] = None, mpn: str = "", sku: str = "", price: Optional[float] = None,
                kind: Optional[str] = None) -> ProductInfo:
    """Parse a product title into brand, model, caliber, capacity, barrel length, rounds per box and cost per round.

    :param title: product title as a store shows it
    :param brand: manufacturer, if known
    :param mpn: manufacturer part number, if known
    :param sku: store SKU, if known
    :param price: price of the listing; with ammo it gives ``cost_per_round``
    :param kind: "firearm" or "ammo"; guessed from the title when omitted

    >>> info = parse_title("Glock 19 Gen5 MOS 9mm 4.02in 15+1 Black")
    >>> info.model.model, info.caliber.name, info.capacity, info.barrel_length
    ('Glock 19 Gen 5 MOS', '9×19mm Parabellum', 15, 4.02)
    >>> parse_title("Federal American Eagle 9mm Luger 115gr FMJ, 50/Box", price=18.99).cost_per_round
    0.3798
    """
    title = title or ""
    if kind not in ("firearm", "ammo"):
        kind = "ammo" if looks_like_ammo(title) else "firearm"
    cals = find_calibers(title)
    if kind == "ammo":
        rounds = rounds_per_box(title)
        return ProductInfo(title=title, kind=kind, brand=brand or "", caliber=cals[0] if cals else None, calibers=cals,
                           rounds=rounds, cost_per_round=cost_per_round(price, rounds) if price else None)
    model = identify_model(title, brand=brand, mpn=mpn, sku=sku)
    return ProductInfo(title=title, kind=kind, brand=model.brand if model else (brand or ""), model=model,
                       caliber=cals[0] if cals else None, calibers=cals, capacity=magazine_capacity(title),
                       barrel_length=barrel_length(title))
