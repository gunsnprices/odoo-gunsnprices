from odoo import api, fields, models

from .. import specs

PARAM_OVERWRITE = "gunsnprices_product_specs.overwrite"
PARAM_FILL_ON_CREATE = "gunsnprices_product_specs.fill_on_create"


def get_flag(env, key):
    """Boolean system parameter (Odoo 20 has typed getters, 18 and 19 store strings)."""
    params = env["ir.config_parameter"].sudo()
    if hasattr(params, "get_bool"):
        return params.get_bool(key)
    return specs.is_true(params.get_param(key))


def set_flag(env, key, value):
    params = env["ir.config_parameter"].sudo()
    if hasattr(params, "set_bool"):
        params.set_bool(key, bool(value))
    else:
        params.set_param(key, bool(value))


# spec key (specs.py) -> product.template field
FIELD_OF = {
    "kind": "gnp_product_kind",
    "brand": "gnp_brand",
    "model_family": "gnp_model_family",
    "model": "gnp_model",
    "generation": "gnp_generation",
    "magazine_capacity": "gnp_magazine_capacity",
    "barrel_length": "gnp_barrel_length",
    "rounds_per_box": "gnp_rounds_per_box",
}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    gnp_product_kind = fields.Selection(
        [("firearm", "Firearm"), ("ammo", "Ammunition")], string="Firearm or Ammo",
        help="Set by Fill Specs when the name reads like ammunition, or when a firearm model is recognized.")
    gnp_brand = fields.Char(string="Brand", help="Brand of the firearm model recognized in the name.")
    gnp_model_family = fields.Char(string="Model Family", help='For example "Glock 19".')
    gnp_model = fields.Char(string="Model", help='Most specific model, for example "Glock 19 Gen 5 MOS".')
    gnp_generation = fields.Char(string="Generation", help='"5", "V", "V3" ...')
    gnp_caliber_id = fields.Many2one("gnp.caliber", string="Caliber", index=True, ondelete="restrict")
    gnp_other_caliber_ids = fields.Many2many(
        "gnp.caliber", "product_template_gnp_caliber_rel", "product_tmpl_id", "caliber_id",
        string="Other Calibers",
        help='Other calibers in the name, for example ".38 Special" on a ".357 Mag / .38 Special" revolver.')
    gnp_caliber_type = fields.Selection(related="gnp_caliber_id.caliber_type", store=True, string="Caliber Class")
    gnp_magazine_capacity = fields.Integer(string="Magazine Capacity", help="Rounds; for 15+1 this is 15.")
    gnp_barrel_length = fields.Float(string="Barrel Length (in)", digits=(16, 2))
    gnp_rounds_per_box = fields.Integer(string="Rounds per Box")
    gnp_cost_per_round = fields.Float(
        string="Cost per Round", digits=(16, 4), compute="_compute_gnp_cost_per_round", store=True,
        help="Sales price divided by rounds per box.")

    @api.depends("list_price", "gnp_rounds_per_box")
    def _compute_gnp_cost_per_round(self):
        for template in self:
            template.gnp_cost_per_round = specs.cost_per_round(template.list_price, template.gnp_rounds_per_box)

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if not self.env.context.get("gnp_no_fill") and get_flag(self.env, PARAM_FILL_ON_CREATE):
            templates._gnp_fill_specs(overwrite=False)
        return templates

    # --- the record protocol used by specs.fill_records ---------------------------------------------------------
    def _gnp_specs_input(self):
        self.ensure_one()
        return {
            "name": self.name or "",
            "brand": self.gnp_brand or "",
            "reference": self.default_code or "",
            "kind": self.gnp_product_kind or "",
        }

    def _gnp_current_specs(self):
        self.ensure_one()
        current = {key: self[fname] for key, fname in FIELD_OF.items()}
        current["caliber"] = self.gnp_caliber_id.code or ""
        current["other_calibers"] = tuple(self.gnp_other_caliber_ids.mapped("code"))
        return current

    def _gnp_write_specs(self, changes, caliber_ids=None):
        self.ensure_one()
        if caliber_ids is None:
            caliber_ids = self._gnp_caliber_ids_by_code()
        vals = {FIELD_OF[key]: value for key, value in changes.items() if key in FIELD_OF}
        if "caliber" in changes and changes["caliber"] in caliber_ids:
            vals["gnp_caliber_id"] = caliber_ids[changes["caliber"]]
        if "other_calibers" in changes:
            ids = [caliber_ids[code] for code in changes["other_calibers"] if code in caliber_ids]
            if ids:
                vals["gnp_other_caliber_ids"] = [(6, 0, ids)]
        if vals:
            self.write(vals)

    # ----------------------------------------------------------------------------------------------------------------
    def _gnp_caliber_ids_by_code(self):
        rows = self.env["gnp.caliber"].with_context(active_test=False).search_read([], ["code"])
        return {row["code"]: row["id"] for row in rows}

    def _gnp_fill_specs(self, overwrite=None):
        """Fill specs from the product names. ``overwrite=None`` uses the setting. Returns specs.fill_records stats."""
        if overwrite is None:
            overwrite = get_flag(self.env, PARAM_OVERWRITE)
        caliber_ids = self._gnp_caliber_ids_by_code()
        return specs.fill_records(
            self, overwrite=overwrite, write=lambda rec, changes: rec._gnp_write_specs(changes, caliber_ids))

    def action_gnp_fill_specs(self):
        """Button and server action "Fill Specs from Name"."""
        stats = self._gnp_fill_specs()
        _ = self.env._
        parts = []
        if stats["updated"]:
            parts.append(_("%(count)s updated", count=stats["updated"]))
        if stats["unchanged"]:
            parts.append(_("%(count)s already up to date", count=stats["unchanged"]))
        if stats["not_found"]:
            parts.append(_("%(count)s with no specs recognized in the name", count=stats["not_found"]))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Fill Specs from Name"),
                "message": ", ".join(parts) or _("No products selected"),
                "type": "success" if stats["updated"] else ("info" if stats["unchanged"] else "warning"),
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
