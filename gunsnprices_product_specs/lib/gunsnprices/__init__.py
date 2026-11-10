"""gunsnprices - parse firearm and ammunition product titles.

Brand and model (Glock 19 Gen 5 MOS), caliber, magazine capacity, barrel length, rounds per box and cost per round.
Built on the model dictionaries and caliber list behind https://gunsnprices.com.
"""
from .calibers import Caliber, find_caliber, find_calibers, list_calibers, normalize_caliber
from .models import ModelMatch, identify_model, list_brands
from .parse import ProductInfo, parse_title
from .specs import barrel_length, cost_per_round, looks_like_ammo, magazine_capacity, rounds_per_box

__version__ = "0.1.2"
__all__ = [
    "parse_title", "ProductInfo",
    "identify_model", "ModelMatch", "list_brands",
    "find_calibers", "find_caliber", "normalize_caliber", "list_calibers", "Caliber",
    "magazine_capacity", "barrel_length", "rounds_per_box", "cost_per_round", "looks_like_ammo",
    "__version__",
]
