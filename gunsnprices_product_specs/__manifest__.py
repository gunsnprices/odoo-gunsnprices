{
    "name": "Firearm & Ammo Specs",
    "summary": "Caliber, model, magazine capacity, barrel length, rounds per box and cost per round "
               "for gun and ammo products, filled in from the product name",
    "description": """
Firearm and ammunition specs on products.

* Fields on products: firearm or ammo, brand, model family, model, generation, caliber, other calibers,
  caliber class, magazine capacity, barrel length, rounds per box and cost per round.
* "Fill Specs from Name" reads product names such as "Glock 19 Gen5 MOS 9mm 4.02in 15+1" and fills the fields,
  for one product or a whole selection. A setting decides whether filled-in values are overwritten.
* 293 calibers with the spellings retailers use: "9mm Luger", "300 blk" or "12ga" find the right caliber
  when you search or import.
* Runs inside Odoo, no external service. The title parser (MIT) and its data (CC BY 4.0) are bundled.
""",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "author": "GunsNPrices",
    "maintainer": "GunsNPrices",
    "website": "https://gunsnprices.com",
    "license": "LGPL-3",
    "depends": ["product"],
    "data": [
        "security/ir.model.access.csv",
        "data/gnp_caliber_data.xml",
        "views/gnp_caliber_views.xml",
        "views/product_template_views.xml",
        "views/res_config_settings_views.xml",
        "data/ir_actions_server.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
