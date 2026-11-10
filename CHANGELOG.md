# Changelog

Module versions follow Odoo's `<series>.<major>.<minor>.<patch>` scheme: 1.0.0 is `18.0.1.0.0` on the 18.0 branch,
`19.0.1.0.0` on 19.0 and `20.0.1.0.0` on 20.0.

## 1.0.0 (2026-11-10)

First release.

- Firearm and ammunition fields on products: firearm or ammo, brand, model family, model, generation, caliber,
  other calibers, caliber class, magazine capacity, barrel length, rounds per box, cost per round (computed from
  the sales price).
- "Fill Specs from Name": button on the product form, server action on product and variant lists (one product or a
  selection), with a summary notification.
- Settings: overwrite existing specs, fill specs when products are created or imported; parser version shown.
- 293 calibers (`gnp.caliber`) with retailer spellings; name search and CSV import understand them
  ("9mm Luger", "300 blk", "12ga").
- Search filters and group-by for caliber, caliber class, brand and model family; optional list columns.
- Bundled title parser: gunsnprices 0.1.2 (MIT code, CC BY 4.0 data). A newer 0.1.x installed with pip is used
  instead.
- Tested on Odoo 18.0, 19.0 and 20.0 Community.
