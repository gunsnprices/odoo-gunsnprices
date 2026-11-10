"""Static checks of the module folder: manifest, data files, store page rules, bundled parser, port tool."""
import ast
import csv
import importlib.util
import json
import re
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "gunsnprices_product_specs"
MANIFEST = ast.literal_eval((MODULE / "__manifest__.py").read_text(encoding="utf-8"))
DESCRIPTION = MODULE / "static" / "description"

sys.path.insert(0, str(ROOT / "tools"))
import port_to  # noqa: E402
import vendor_gunsnprices  # noqa: E402


def png_size(path: Path):
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", head[16:24])


# --- manifest ----------------------------------------------------------------------------------------------------------

def test_manifest_keys():
    assert re.fullmatch(r"\d+\.0\.\d+\.\d+\.\d+", MANIFEST["version"])
    assert MANIFEST["license"] == "LGPL-3"
    assert MANIFEST["author"] == "GunsNPrices"
    assert MANIFEST["website"] == "https://gunsnprices.com"
    assert MANIFEST["depends"] == ["product"]
    assert MANIFEST["installable"] is True
    assert "price" not in MANIFEST, "free app: no price key"
    assert "external_dependencies" not in MANIFEST, "the parser is bundled; a pip dependency would block installs"
    assert len(MANIFEST["name"]) <= 25, "Odoo Apps: name of at most 25 characters"


def test_manifest_files_exist():
    for name in MANIFEST["data"] + MANIFEST["images"]:
        assert (MODULE / name).is_file(), name


def test_license_file_matches_manifest():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in text and "Version 3" in text


def test_description_rst_renders():
    docutils_core = pytest.importorskip("docutils.core")
    import io
    errors = io.StringIO()
    docutils_core.publish_doctree(MANIFEST["description"],
                                  settings_overrides={"report_level": 2, "halt_level": 5, "warning_stream": errors})
    assert errors.getvalue() == ""


def test_images():
    assert png_size(DESCRIPTION / "icon.png") == (256, 256)
    assert png_size(DESCRIPTION / "banner.png") == (560, 280)


# --- data files ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", sorted(str(p.relative_to(ROOT)) for p in MODULE.rglob("*.xml")))
def test_xml_well_formed(path):
    ET.parse(ROOT / path)


def test_caliber_data_matches_bundled_list():
    tree = ET.parse(MODULE / "data" / "gnp_caliber_data.xml")
    records = {r.find("field[@name='code']").text: r for r in tree.getroot().iter("record")}
    source = json.loads((MODULE / "lib" / "gunsnprices" / "data" / "calibers.json").read_text(encoding="utf-8"))["calibers"]
    assert len(records) == len(source) == 293
    for cal in source:
        rec = records[cal["id"]]
        assert rec.find("field[@name='name']").text == cal["name"]
        assert rec.find("field[@name='caliber_type']").text == cal["type"]
    sequences = sorted(int(r.find("field[@name='sequence']").text) for r in records.values())
    assert sequences == list(range(1, 294))


def test_access_rights_csv():
    rows = list(csv.DictReader((MODULE / "security" / "ir.model.access.csv").open(encoding="utf-8")))
    assert {r["model_id:id"] for r in rows} == {"model_gnp_caliber"}
    admin = next(r for r in rows if r["group_id:id"] == "base.group_system")
    assert [admin[k] for k in ("perm_read", "perm_write", "perm_create", "perm_unlink")] == ["1"] * 4
    for row in rows:
        if row["group_id:id"] != "base.group_system":
            assert (row["perm_write"], row["perm_create"], row["perm_unlink"]) == ("0", "0", "0")


# --- store page (static/description/index.html) ------------------------------------------------------------------------

ALLOWED_STYLE = re.compile(r"^(color|font(-[a-z]+)?|margin(-[a-z]+)?|padding(-[a-z]+)?|border(-[a-z]+)*)$")


def store_page():
    html = pytest.importorskip("lxml.html")
    return html.fromstring((DESCRIPTION / "index.html").read_text(encoding="utf-8"))


def test_store_page_has_no_scripts_or_forbidden_tags():
    doc = store_page()
    for tag in ("script", "iframe", "form", "input", "object", "embed", "link", "style"):
        assert not doc.xpath(f"//{tag}"), tag
    for el in doc.iter():
        for attr in el.attrib:
            assert not attr.startswith("on"), f"event handler {attr} on <{el.tag}>"


def test_store_page_links():
    """Odoo Apps keeps links to static/description files, YouTube, Teams, mailto: and skype: only."""
    doc = store_page()
    for a in doc.xpath("//a[@href]"):
        href = a.get("href")
        assert href.startswith(("mailto:", "skype:", "https://www.youtube.com/", "https://teams.microsoft.com/")) or \
            not re.match(r"^[a-z]+:|^//", href), f"external link {href}"


def test_store_page_images_exist():
    doc = store_page()
    images = doc.xpath("//img/@src")
    assert images
    for src in images:
        assert not re.match(r"^[a-z]+:|^//", src), f"remote image {src}"
        path = DESCRIPTION / src
        assert path.is_file(), src
        assert path.suffix in (".png", ".gif", ".jpg", ".jpeg")


def test_store_page_inline_styles():
    doc = store_page()
    for el in doc.xpath("//*[@style]"):
        for decl in filter(None, (d.strip() for d in el.get("style").split(";"))):
            prop = decl.split(":", 1)[0].strip().lower()
            assert ALLOWED_STYLE.match(prop), f"style property {prop!r} on <{el.tag}>"


# --- bundled parser ------------------------------------------------------------------------------------------------------

def test_bundled_copy_matches_pypi_release():
    """When the PyPI package of the same version is installed, the bundled copy equals it plus the documented patch."""
    spec = importlib.util.find_spec("gunsnprices")
    if spec is None:
        pytest.skip("gunsnprices is not installed (pip install gunsnprices==0.1.2 to run this check)")
    upstream = Path(spec.origin).parent
    bundled = MODULE / "lib" / "gunsnprices"
    version = re.search(r'__version__ = "([^"]+)"', (upstream / "__init__.py").read_text()).group(1)
    ours = re.search(r'__version__ = "([^"]+)"', (bundled / "__init__.py").read_text()).group(1)
    if version != ours:
        pytest.skip(f"installed gunsnprices {version} is not the bundled {ours}")
    for name in vendor_gunsnprices.CODE:
        assert (bundled / name).read_text(encoding="utf-8") == \
            vendor_gunsnprices.patch((upstream / name).read_text(encoding="utf-8")), name
    for name in vendor_gunsnprices.DATA:
        assert (bundled / name).read_bytes() == (upstream / name).read_bytes(), name


def test_bundled_copy_has_licenses():
    bundled = MODULE / "lib" / "gunsnprices"
    assert "MIT License" in (bundled / "LICENSE").read_text()
    assert "CC BY 4.0" in (bundled / "LICENSE-DATA").read_text()


# --- port tool -----------------------------------------------------------------------------------------------------------

def test_port_to_19(tmp_path):
    module = tmp_path / "gunsnprices_product_specs"
    shutil.copytree(MODULE, module)
    port_to.port("19.0", module)
    manifest = ast.literal_eval((module / "__manifest__.py").read_text())
    assert manifest["version"].startswith("19.0.")
    assert "security/ir.model.access.csv" in manifest["data"]


def test_port_to_20_converts_access_rights(tmp_path):
    module = tmp_path / "gunsnprices_product_specs"
    shutil.copytree(MODULE, module)
    port_to.port("20.0", module)
    manifest = ast.literal_eval((module / "__manifest__.py").read_text())
    assert manifest["version"].startswith("20.0.")
    assert "security/ir.access.csv" in manifest["data"]
    assert not (module / "security" / "ir.model.access.csv").exists()
    rows = list(csv.DictReader((module / "security" / "ir.access.csv").open()))
    assert {r["model_id"] for r in rows} == {"gnp.caliber"}
    assert {r["group_id/id"]: r["operation"] for r in rows} == {
        "base.group_user": "r", "base.group_portal": "r", "base.group_public": "r", "base.group_system": "crud"}
