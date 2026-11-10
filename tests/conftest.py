"""Import the module's pure-Python parts (parser.py, specs.py, lib/) without Odoo.

gunsnprices_product_specs/__init__.py imports the Odoo models, so a bare package object pointing at the module
folder is registered first: submodules then import normally and __init__.py is never run.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = ROOT / "gunsnprices_product_specs"

if "gunsnprices_product_specs" not in sys.modules:
    package = types.ModuleType("gunsnprices_product_specs")
    package.__path__ = [str(MODULE_DIR)]
    sys.modules["gunsnprices_product_specs"] = package
