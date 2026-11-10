"""Draw static/description/icon.png (256x256) and banner.png (560x280).

The banner shows real output of the bundled parser for one product name (computed here, not typed in).
Needs Pillow and the GunsNPrices brand icon:  python tools/make_images.py /path/to/gunsnprices-icon-512.png
Fonts: Arial / Arial Bold from macOS; pass other .ttf files with GNP_FONT and GNP_FONT_BOLD.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "gunsnprices_product_specs" / "static" / "description"
sys.path.insert(0, str(ROOT / "gunsnprices_product_specs" / "lib"))
import gunsnprices  # noqa: E402  (the bundled copy)

ORANGE = (241, 90, 41)
INK = (31, 41, 55)
MUTED = (107, 114, 128)
CHIP = (254, 236, 228)
FONT = os.environ.get("GNP_FONT", "/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = os.environ.get("GNP_FONT_BOLD", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
NAME = "Glock 19 Gen5 MOS 9mm 4.02in 15+1"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def icon(brand_icon: Path) -> Image.Image:
    im = Image.open(brand_icon).convert("RGBA").resize((256, 256), Image.LANCZOS)
    im.save(OUT / "icon.png", optimize=True)
    return im


def banner(logo: Image.Image) -> None:
    scale = 2  # draw at 2x, then downsample for smooth text
    w, h = 560 * scale, 280 * scale
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 10 * scale], fill=ORANGE)
    small = logo.resize((64 * scale, 64 * scale), Image.LANCZOS)
    im.paste(small, (28 * scale, 30 * scale), small)
    d.text((108 * scale, 34 * scale), "Firearm & Ammo Specs", font=font(30 * scale, True), fill=INK)
    d.text((108 * scale, 72 * scale), "for Odoo products, filled in from the product name",
           font=font(15 * scale), fill=MUTED)

    info = gunsnprices.parse_title(NAME)
    y = 118 * scale
    d.rounded_rectangle([28 * scale, y, 532 * scale, y + 40 * scale], radius=8 * scale,
                        outline=(209, 213, 219), width=2 * scale)
    d.text((44 * scale, y + 10 * scale), NAME, font=font(17 * scale, True), fill=INK)
    d.text((280 * scale - 6 * scale, y + 44 * scale), "↓", font=font(20 * scale, True), fill=ORANGE)

    chips = [
        ("Model", info.model.model),
        ("Caliber", info.caliber.name),
        ("Magazine", f"{info.capacity} rd"),
        ("Barrel", f"{info.barrel_length:g} in"),
    ]
    x, y = 28 * scale, 190 * scale
    for label, value in chips:
        lw = d.textlength(label, font=font(11 * scale))
        vw = d.textlength(value, font=font(14 * scale, True))
        cw = max(lw, vw) + 20 * scale
        if x + cw > 532 * scale:
            x, y = 28 * scale, y + 50 * scale
        d.rounded_rectangle([x, y, x + cw, y + 44 * scale], radius=8 * scale, fill=CHIP)
        d.text((x + 10 * scale, y + 5 * scale), label, font=font(11 * scale), fill=MUTED)
        d.text((x + 10 * scale, y + 20 * scale), value, font=font(14 * scale, True), fill=INK)
        x += cw + 10 * scale
    d.text((28 * scale, 252 * scale), "293 calibers  ·  50 brands  ·  rounds per box & cost per round for ammo",
           font=font(12 * scale), fill=MUTED)
    im.resize((560, 280), Image.LANCZOS).save(OUT / "banner.png", optimize=True)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    OUT.mkdir(parents=True, exist_ok=True)
    banner(icon(Path(sys.argv[1]).expanduser()))
    print("wrote", OUT / "icon.png", "and", OUT / "banner.png")


if __name__ == "__main__":
    main()
