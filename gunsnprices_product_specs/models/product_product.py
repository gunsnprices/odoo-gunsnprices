from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_gnp_fill_specs(self):
        """Server action on variants: specs live on the product template."""
        return self.product_tmpl_id.action_gnp_fill_specs()
