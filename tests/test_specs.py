"""The fill logic without Odoo: parsing, the write plan, and fill_records against fake records (the ORM boundary)."""
import types

import pytest

from gunsnprices_product_specs import parser, specs
from gunsnprices_product_specs.specs import SPEC_KEYS, fill_records, parse_product, plan_update


# --- parse_product -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name, kwargs, expected", [
    ("Glock 19 Gen5 MOS 9mm 4.02in 15+1 Black", {}, {
        "kind": "firearm", "brand": "Glock", "model_family": "Glock 19", "model": "Glock 19 Gen 5 MOS",
        "generation": "5", "caliber": "9x19mmparabellum", "magazine_capacity": 15, "barrel_length": 4.02}),
    ("Federal American Eagle 9mm Luger 115gr FMJ, 50/Box", {}, {
        "kind": "ammo", "caliber": "9x19mmparabellum", "rounds_per_box": 50}),
    ("Ruger GP100 .357 Mag / .38 Special 4.2in Revolver", {}, {
        "kind": "firearm", "brand": "Ruger", "model_family": "Ruger GP100", "model": "Ruger GP100",
        "caliber": "357mag", "other_calibers": ("38swspecial",), "barrel_length": 4.2}),
    ("Winchester Super-X 12 Gauge 2-3/4\" 00 Buckshot 5 Rounds", {}, {
        "kind": "ammo", "caliber": "12gauge", "rounds_per_box": 5}),
    # Glock part number: model and generation from the reference
    ("Glock 19 9mm Pistol", {"reference": "PA195S203MOS"}, {
        "kind": "firearm", "brand": "Glock", "model_family": "Glock 19", "model": "Glock 19 Gen 5 MOS",
        "generation": "5", "caliber": "9x19mmparabellum"}),
    # an accessory gets no model and no kind, but keeps caliber and capacity
    ("Magpul PMAG 30rd 5.56 Magazine", {}, {"caliber": "5-56x45mmnato", "magazine_capacity": 30}),
    ("Blue Cotton T-Shirt XL", {}, {}),
    ("", {}, {}),
])
def test_parse_product(name, kwargs, expected):
    assert parse_product(name, **kwargs) == expected


def test_parse_product_known_kind_is_not_returned_and_steers_parsing():
    name = "Glock 19 Gen 5 9mm Pistol Bundle with 50 Rounds of Ammo"
    assert parse_product(name)["kind"] == "ammo"
    as_firearm = parse_product(name, kind="firearm")
    assert "kind" not in as_firearm
    assert as_firearm["model"] == "Glock 19 Gen 5"


def test_parse_product_brand_hint():
    # "P365" alone isn't tied to a brand; the brand field makes it a Sig Sauer
    assert "model" not in parse_product("P365 XL 9mm 3.1in 12rd")
    assert parse_product("P365 XL 9mm 3.1in 12rd", brand="Sig Sauer")["model"] == "Sig Sauer P365 XL"


def test_found_keys_are_spec_keys():
    found = parse_product("Ruger GP100 .357 Mag / .38 Special 4.2in Revolver")
    assert set(found) <= set(SPEC_KEYS)


# --- plan_update --------------------------------------------------------------------------------------------------------

EMPTY = {"kind": False, "brand": False, "model_family": False, "model": False, "generation": False, "caliber": "",
         "other_calibers": (), "magazine_capacity": 0, "barrel_length": 0.0, "rounds_per_box": 0}
GLOCK = parse_product("Glock 19 Gen5 MOS 9mm 4.02in 15+1 Black")


def test_plan_fills_empty_fields():
    assert plan_update(EMPTY, GLOCK) == GLOCK


def test_plan_keeps_filled_fields_without_overwrite():
    current = dict(EMPTY, magazine_capacity=17, brand="Glock")
    changes = plan_update(current, GLOCK)
    assert "magazine_capacity" not in changes and "brand" not in changes
    assert changes["model"] == "Glock 19 Gen 5 MOS"


def test_plan_overwrite_replaces_but_never_clears():
    current = dict(EMPTY, magazine_capacity=17, rounds_per_box=50)
    changes = plan_update(current, GLOCK, overwrite=True)
    assert changes["magazine_capacity"] == 15
    assert "rounds_per_box" not in changes  # nothing found -> left alone


def test_plan_nothing_to_change():
    current = dict(EMPTY, **GLOCK)
    assert plan_update(current, GLOCK) == {}
    assert plan_update(current, GLOCK, overwrite=True) == {}


def test_plan_float_tolerance():
    current = dict(EMPTY, **dict(GLOCK, barrel_length=4.0200000001))
    assert "barrel_length" not in plan_update(current, GLOCK, overwrite=True)


def test_plan_calibers():
    found = parse_product("Ruger GP100 .357 Mag / .38 Special 4.2in Revolver")
    assert plan_update(EMPTY, found)["other_calibers"] == ("38swspecial",)
    # main caliber set by hand and kept: every caliber in the name goes to "other calibers"
    kept = plan_update(dict(EMPTY, caliber="9x19mmparabellum"), found)
    assert "caliber" not in kept
    assert kept["other_calibers"] == ("357mag", "38swspecial")
    # with overwrite the main caliber is replaced
    replaced = plan_update(dict(EMPTY, caliber="9x19mmparabellum"), found, overwrite=True)
    assert replaced["caliber"] == "357mag"
    assert replaced["other_calibers"] == ("38swspecial",)
    # same calibers in another order: no change
    same = dict(EMPTY, caliber="357mag", other_calibers=("38swspecial",))
    changes = plan_update(same, found, overwrite=True)
    assert "caliber" not in changes and "other_calibers" not in changes


# --- fill_records (fake records stand in for the ORM) -----------------------------------------------------------------

class FakeRecord:
    def __init__(self, name, **current):
        self.name = name
        self.current = dict(EMPTY, **current)
        self.written = []

    def _gnp_specs_input(self):
        return {"name": self.name, "brand": self.current["brand"] or "", "reference": "",
                "kind": self.current["kind"] or ""}

    def _gnp_current_specs(self):
        return dict(self.current)

    def _gnp_write_specs(self, changes):
        self.written.append(changes)
        self.current.update(changes)


def test_fill_records_counts_and_writes():
    records = [
        FakeRecord("Glock 19 Gen5 MOS 9mm 4.02in 15+1 Black"),
        FakeRecord("CCI Mini-Mag 22 LR 40gr 100 Rounds"),
        FakeRecord("Gift card"),
    ]
    assert fill_records(records) == {"updated": 2, "unchanged": 0, "not_found": 1}
    assert records[0].current["model"] == "Glock 19 Gen 5 MOS"
    assert records[1].current["rounds_per_box"] == 100 and records[1].current["kind"] == "ammo"
    assert records[2].written == []
    # second run: nothing left to write
    assert fill_records(records) == {"updated": 0, "unchanged": 2, "not_found": 1}
    assert len(records[0].written) == 1


def test_fill_records_overwrite_and_custom_writer():
    record = FakeRecord("Glock 19 Gen5 9mm 4.02in 15+1", magazine_capacity=17)
    calls = []
    stats = fill_records([record], overwrite=True, write=lambda rec, changes: calls.append((rec, changes)))
    assert stats["updated"] == 1
    assert calls[0][0] is record and calls[0][1]["magazine_capacity"] == 15
    assert record.written == []  # the custom writer replaced _gnp_write_specs


# --- helpers ------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    ("True", True), ("1", True), ("yes", True), (" on ", True),
    ("False", False), ("0", False), ("", False), (None, False), (False, False),
])
def test_is_true(value, expected):
    assert specs.is_true(value) is expected


def test_cost_per_round():
    assert specs.cost_per_round(18.99, 50) == 0.3798
    assert specs.cost_per_round(0, 50) == 0.0
    assert specs.cost_per_round(18.99, 0) == 0.0


# --- which parser copy is used -----------------------------------------------------------------------------------------

def test_bundled_parser():
    assert parser._bundled.__version__ == "0.1.2"
    assert parser._bundled.__name__ == "gunsnprices_product_specs.lib.gunsnprices"
    assert len(parser._bundled.list_calibers()) == 293
    assert len(parser._bundled.list_brands()) == 50


@pytest.mark.parametrize("version, expected", [
    ("0.1.2", (0, 1, 2)), ("0.1.10", (0, 1, 10)), ("0.1.3rc1", (0, 1, 3)), ("1.0", (1, 0)), ("", ()), ("dev", ()),
])
def test_version_tuple(version, expected):
    assert parser.version_tuple(version) == expected


@pytest.mark.parametrize("installed_version, expected", [
    (None, "bundled"),        # not installed
    ("0.1.2", "bundled"),     # same release
    ("0.1.1", "bundled"),     # older
    ("0.1.3", "installed"),   # newer in the same series
    ("0.1.10", "installed"),
    ("0.2.0", "bundled"),     # other series: API may differ
    ("1.0.0", "bundled"),
    ("", "bundled"),
])
def test_pick(installed_version, expected):
    bundled = types.SimpleNamespace(__version__="0.1.2")
    installed = None if installed_version is None else types.SimpleNamespace(__version__=installed_version)
    module, source = parser.pick(bundled, installed)
    assert source == expected
    assert module is (installed if expected == "installed" else bundled)
