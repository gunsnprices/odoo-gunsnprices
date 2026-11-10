from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCaliber(TransactionCase):

    def test_calibers_seeded(self):
        data = self.env["ir.model.data"].search(
            [("module", "=", "gunsnprices_product_specs"), ("model", "=", "gnp.caliber")])
        self.assertEqual(len(data), 293)
        nine = self.env.ref("gunsnprices_product_specs.caliber_9x19mmparabellum")
        self.assertEqual(nine.name, "9×19mm Parabellum")
        self.assertEqual(nine.caliber_type, "handgun")
        self.assertEqual(nine.sequence, 1, "the most listed caliber comes first")
        self.assertIn("9mm Luger", nine.aliases)

    def test_name_search_understands_retailer_spellings(self):
        Caliber = self.env["gnp.caliber"]
        for typed, xmlid in [
            ("9mm luger", "caliber_9x19mmparabellum"),
            ("300 blk", "caliber_300aacblackout"),
            ("12ga", "caliber_12gauge"),
            ("5.56 NATO", "caliber_5_56x45mmnato"),
        ]:
            expected = self.env.ref(f"gunsnprices_product_specs.{xmlid}")
            found = Caliber.browse([r[0] for r in Caliber.name_search(typed)])
            self.assertIn(expected, found, typed)

    def test_import_matches_caliber_spelling(self):
        result = self.env["product.template"].load(["name", "gnp_caliber_id"], [["Test pistol", "9mm Luger"]])
        self.assertFalse([m for m in result["messages"] if m["type"] == "error"], result["messages"])
        template = self.env["product.template"].browse(result["ids"])
        self.assertEqual(template.gnp_caliber_id, self.env.ref("gunsnprices_product_specs.caliber_9x19mmparabellum"))

    def test_code_is_unique(self):
        from psycopg2 import IntegrityError

        from odoo.tools import mute_logger
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["gnp.caliber"].create({"name": "Duplicate", "code": "9x19mmparabellum", "caliber_type": "handgun"})

    def test_caliber_in_use_cannot_be_deleted(self):
        from odoo.exceptions import UserError
        nine = self.env.ref("gunsnprices_product_specs.caliber_9x19mmparabellum")
        self.env["product.template"].create({"name": "Test product", "gnp_caliber_id": nine.id})
        with self.assertRaises(UserError):
            nine.unlink()
        other = self.env.ref("gunsnprices_product_specs.caliber_12gauge")
        self.env["product.template"].create(
            {"name": "Archived test product", "active": False, "gnp_other_caliber_ids": [(6, 0, other.ids)]})
        with self.assertRaises(UserError):
            other.unlink()
        spare = self.env["gnp.caliber"].create({"name": "Test caliber", "code": "testcaliber", "caliber_type": "rifle"})
        spare.unlink()
        self.assertFalse(spare.exists())

    def test_product_count_and_action(self):
        nine = self.env.ref("gunsnprices_product_specs.caliber_9x19mmparabellum")
        before = nine.product_count
        self.env["product.template"].create({"name": "Test product A", "gnp_caliber_id": nine.id})
        self.env["product.template"].create({"name": "Test product B", "gnp_other_caliber_ids": [(6, 0, nine.ids)]})
        nine.invalidate_recordset(["product_count"])
        self.assertEqual(nine.product_count, before + 2)
        action = nine.action_view_products()
        self.assertEqual(action["res_model"], "product.template")
        self.assertEqual(self.env["product.template"].search_count(action["domain"]), before + 2)
