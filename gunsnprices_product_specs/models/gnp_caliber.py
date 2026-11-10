from collections.abc import Iterable

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..parser import gnp

try:  # Odoo 19+
    from odoo.fields import Domain

    def _or(domains):
        return Domain.OR(domains)
except ImportError:  # Odoo 18
    from odoo.osv import expression

    def _or(domains):
        return expression.OR(domains)


CALIBER_TYPES = [
    ("handgun", "Handgun"),
    ("rifle", "Rifle"),
    ("rimfire", "Rimfire"),
    ("shotgun", "Shotgun"),
    ("airgun", "Airgun"),
    ("muzzleloader", "Muzzleloader"),
]


class GnpCaliber(models.Model):
    _name = "gnp.caliber"
    _description = "Caliber"
    _order = "sequence, name"
    _rec_names_search = ["name", "code", "aliases"]

    name = fields.Char(required=True)
    code = fields.Char(
        required=True, index=True,
        help="Stable id of the caliber, e.g. 9x19mmparabellum. Products are matched to calibers by this code.")
    caliber_type = fields.Selection(CALIBER_TYPES, string="Class", required=True, default="rifle")
    aliases = fields.Text(
        string="Spellings",
        help="Other ways retailers write this caliber, one per line. Search and import match them too.")
    sequence = fields.Integer(default=1000, help="Most common calibers come first.")
    active = fields.Boolean(default=True)
    reference_url = fields.Char(
        string="Reference Page",
        help="Page with listings and prices for this caliber on gunsnprices.com, from the caliber dataset.")
    product_count = fields.Integer(compute="_compute_product_count", string="Products")

    if hasattr(models, "Constraint"):  # Odoo 19+
        _code_uniq = models.Constraint("UNIQUE(code)", "Each caliber code can only be used once.")
    else:  # Odoo 18
        _sql_constraints = [("code_uniq", "UNIQUE(code)", "Each caliber code can only be used once.")]

    def _products_domain(self):
        return ["|", ("gnp_caliber_id", "in", self.ids), ("gnp_other_caliber_ids", "in", self.ids)]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_by_products(self):
        """A caliber that products use is archived, not deleted (the database link itself is "set null", so
        uninstalling the module can remove the calibers without errors)."""
        templates = self.env["product.template"].with_context(active_test=False)
        if templates.search_count(self._products_domain(), limit=1):
            raise UserError(self.env._("Products use this caliber. Archive it instead of deleting it."))

    def _compute_product_count(self):
        templates = self.env["product.template"]
        for caliber in self:
            caliber.product_count = templates.search_count(caliber._products_domain()) if caliber.id else 0

    def _search_display_name(self, operator, value):
        """Typing or importing "9mm luger", "300 blk" or "12ga" also finds the caliber it stands for."""
        domain = super()._search_display_name(operator, value)
        if operator not in ("ilike", "=ilike", "like", "=like", "=", "in"):
            return domain
        # Odoo 19+ turns name_search(operator="=") into ("display_name", "in", OrderedSet([value]))
        values = [value] if isinstance(value, str) else list(value) if isinstance(value, Iterable) else []
        codes = set()
        for text in values:
            caliber = gnp.normalize_caliber(text) if isinstance(text, str) and text.strip() else None
            if caliber:
                codes.add(caliber.id)
        if codes:
            domain = _or([domain, [("code", "in", sorted(codes))]])
        return domain

    def action_view_products(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "product.template",
            "view_mode": "list,form",
            "domain": self._products_domain(),
            "context": {"default_gnp_caliber_id": self.id},
        }
