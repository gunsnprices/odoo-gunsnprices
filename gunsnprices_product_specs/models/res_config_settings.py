from odoo import fields, models

from ..parser import SOURCE, VERSION
from .product_template import PARAM_FILL_ON_CREATE, PARAM_OVERWRITE


def parser_label():
    where = "bundled with the module" if SOURCE == "bundled" else "installed with pip"
    return f"gunsnprices {VERSION} ({where})"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gnp_overwrite_specs = fields.Boolean(
        string="Overwrite Existing Specs", config_parameter=PARAM_OVERWRITE,
        help="Off: Fill Specs only writes empty fields. On: values found in the name replace the current ones.")
    gnp_fill_on_create = fields.Boolean(
        string="Fill Specs on Product Creation", config_parameter=PARAM_FILL_ON_CREATE,
        help="Read the name of every new product, including products created by an import.")
    # a default, not a compute: the settings form shows defaults of new records
    gnp_parser_info = fields.Char(string="Title Parser", readonly=True, default=lambda self: parser_label())
