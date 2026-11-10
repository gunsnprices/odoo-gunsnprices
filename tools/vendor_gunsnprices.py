"""Copy the gunsnprices title parser into the module (gunsnprices_product_specs/lib/gunsnprices).

Usage:
    python tools/vendor_gunsnprices.py /path/to/gunsnprices-X.Y.Z-py3-none-any.whl
    python tools/vendor_gunsnprices.py /path/to/library/python/src/gunsnprices

Odoo modules are installed by copying a folder into the addons path, so the parser ships inside the module.
One change is made to the upstream files: the data files are loaded from the vendored package
(``resources.files(__package__)``) instead of from the top-level ``gunsnprices`` package. Nothing else is touched;
tests/test_package.py checks that against the PyPI release when it is installed.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "gunsnprices_product_specs" / "lib" / "gunsnprices"
CODE = ["__init__.py", "calibers.py", "models.py", "parse.py", "specs.py"]
DATA = ["data/calibers.json", "data/models.json"]
LICENSES = ["LICENSE", "LICENSE-DATA"]
UPSTREAM_LOAD = 'resources.files("gunsnprices")'
VENDORED_LOAD = "resources.files(__package__)"


def patch(text: str) -> str:
    """The only change made to upstream code."""
    return text.replace(UPSTREAM_LOAD, VENDORED_LOAD)


def _source(arg: Path, tmp: Path) -> tuple[Path, Path]:
    """Return (package dir, dir holding LICENSE files)."""
    if arg.suffix == ".whl":
        with zipfile.ZipFile(arg) as z:
            z.extractall(tmp)
        lic = next(tmp.glob("gunsnprices-*.dist-info/licenses"))
        return tmp / "gunsnprices", lic
    return arg, arg.parent.parent  # src/gunsnprices -> repo root with LICENSE files


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    with tempfile.TemporaryDirectory() as t:
        pkg, lic = _source(Path(argv[1]).expanduser().resolve(), Path(t))
        if DEST.exists():
            shutil.rmtree(DEST)
        (DEST / "data").mkdir(parents=True)
        for name in CODE:
            text = (pkg / name).read_text(encoding="utf-8")
            new = patch(text)
            (DEST / name).write_text(new, encoding="utf-8")
            if new != text:
                print(f"patched {name}")
        for name in DATA:
            shutil.copyfile(pkg / name, DEST / name)
        for name in LICENSES:
            shutil.copyfile(lic / name, DEST / name)
    version = next(line for line in (DEST / "__init__.py").read_text().splitlines() if line.startswith("__version__"))
    print(f"vendored {version} into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
