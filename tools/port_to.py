"""Adapt the module to another Odoo series, in place.

    python tools/port_to.py 19.0 [path/to/gunsnprices_product_specs]

The code runs unchanged on Odoo 18.0, 19.0 and 20.0; what differs per branch:

* the manifest version prefix (18.0.x.y.z -> 19.0.x.y.z);
* from 20.0 on, access rights are ``ir.access`` records (security/ir.access.csv) instead of
  ``ir.model.access`` (security/ir.model.access.csv); Odoo 20 has no ir.model.access model any more.

It works in both directions (20.0 -> 19.0 turns ir.access.csv back into ir.model.access.csv), so a fix made on any
branch can be carried to the others.

Typical use when opening a new branch:  git switch -c 19.0 && python tools/port_to.py 19.0 && git commit -am "19.0"
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "gunsnprices_product_specs"
OLD_ACL = "security/ir.model.access.csv"
NEW_ACL = "security/ir.access.csv"


def acl_to_ir_access(text: str) -> str:
    """ir.model.access rows -> ir.access rows (Odoo 20+)."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "name", "model_id", "group_id/id", "operation", "domain"])
    for row in csv.DictReader(io.StringIO(text)):
        perms = ("perm_create", "perm_read", "perm_write", "perm_unlink")
        ops = "".join(letter for letter, perm in zip("crud", perms, strict=True) if row[perm] == "1")
        model = row["model_id:id"].split(".")[-1].removeprefix("model_").replace("_", ".")
        writer.writerow([row["id"], row["name"], model, row["group_id:id"], ops, ""])
    return out.getvalue()


def ir_access_to_acl(text: str) -> str:
    """ir.access rows -> ir.model.access rows (Odoo 19 and older). Record rules (a domain) have no equivalent there."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "name", "model_id:id", "group_id:id", "perm_read", "perm_write", "perm_create", "perm_unlink"])
    for row in csv.DictReader(io.StringIO(text)):
        if (row.get("domain") or "").strip():
            raise SystemExit(f"{row['id']}: an ir.access row with a domain is a record rule, port it by hand")
        ops = row["operation"]
        model = "model_" + row["model_id"].replace(".", "_")
        # perm_read, perm_write, perm_create, perm_unlink <- r(ead), u(pdate), c(reate), d(elete)
        writer.writerow([row["id"], row["name"], model, row["group_id/id"]] + ["1" if c in ops else "0" for c in "rucd"])
    return out.getvalue()


def _convert(module: Path, src: str, dst: str, convert, manifest_text: str) -> str:
    (module / dst).write_text(convert((module / src).read_text(encoding="utf-8")), encoding="utf-8")
    (module / src).unlink()
    return manifest_text.replace(f'"{src}"', f'"{dst}"')


def port(series: str, module: Path) -> None:
    if not re.fullmatch(r"\d+\.0", series):
        raise SystemExit(f"series must look like 19.0, not {series!r}")
    manifest = module / "__manifest__.py"
    text = manifest.read_text(encoding="utf-8")
    text, n = re.subn(r'("version": ")\d+\.0\.', rf"\g<1>{series}.", text)
    if n != 1:
        raise SystemExit("version not found in the manifest")
    if int(series.split(".")[0]) >= 20 and (module / OLD_ACL).exists():
        text = _convert(module, OLD_ACL, NEW_ACL, acl_to_ir_access, text)
    elif int(series.split(".")[0]) < 20 and (module / NEW_ACL).exists():
        text = _convert(module, NEW_ACL, OLD_ACL, ir_access_to_acl, text)
    manifest.write_text(text, encoding="utf-8")
    print(f"{module.name}: ported to {series}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    port(sys.argv[1], Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else MODULE)
