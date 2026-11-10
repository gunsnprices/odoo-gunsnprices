from odoo.tests import Form, TransactionCase, tagged

from ..models.product_template import PARAM_FILL_ON_CREATE, PARAM_OVERWRITE, get_flag, set_flag


@tagged("post_install", "-at_install")
class TestFillSpecs(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Template = cls.env["product.template"]
        set_flag(cls.env, PARAM_OVERWRITE, False)
        set_flag(cls.env, PARAM_FILL_ON_CREATE, False)

    def caliber(self, code):
        return self.env["gnp.caliber"].search([("code", "=", code)])

    def test_firearm(self):
        glock = self.Template.create({"name": "Glock 19 Gen5 MOS 9mm 4.02in 15+1 Black"})
        action = glock.action_gnp_fill_specs()
        self.assertEqual(action["params"]["type"], "success")
        self.assertRecordValues(glock, [{
            "gnp_product_kind": "firearm",
            "gnp_brand": "Glock",
            "gnp_model_family": "Glock 19",
            "gnp_model": "Glock 19 Gen 5 MOS",
            "gnp_generation": "5",
            "gnp_caliber_id": self.caliber("9x19mmparabellum").id,
            "gnp_magazine_capacity": 15,
            "gnp_barrel_length": 4.02,
            "gnp_rounds_per_box": 0,
        }])
        self.assertEqual(glock.gnp_caliber_type, "handgun")

    def test_ammo_and_cost_per_round(self):
        ammo = self.Template.create({"name": "Federal American Eagle 9mm Luger 115gr FMJ, 50/Box", "list_price": 18.99})
        ammo.action_gnp_fill_specs()
        self.assertEqual(ammo.gnp_product_kind, "ammo")
        self.assertEqual(ammo.gnp_rounds_per_box, 50)
        self.assertEqual(ammo.gnp_caliber_id, self.caliber("9x19mmparabellum"))
        self.assertAlmostEqual(ammo.gnp_cost_per_round, 0.3798, places=4)
        ammo.list_price = 25.0
        self.assertAlmostEqual(ammo.gnp_cost_per_round, 0.5, places=4)
        self.assertFalse(ammo.gnp_model)

    def test_two_calibers(self):
        revolver = self.Template.create({"name": "Ruger GP100 .357 Mag / .38 Special 4.2in Revolver"})
        revolver.action_gnp_fill_specs()
        self.assertEqual(revolver.gnp_caliber_id, self.caliber("357mag"))
        self.assertEqual(revolver.gnp_other_caliber_ids, self.caliber("38swspecial"))
        self.assertEqual(revolver.gnp_barrel_length, 4.2)

    def test_keeps_filled_values_unless_overwrite(self):
        glock = self.Template.create({"name": "Glock 19 Gen5 9mm 4.02in 15+1", "gnp_magazine_capacity": 17})
        glock.action_gnp_fill_specs()
        self.assertEqual(glock.gnp_magazine_capacity, 17, "filled-in value kept")
        self.assertEqual(glock.gnp_model, "Glock 19 Gen 5", "empty field filled")
        set_flag(self.env, PARAM_OVERWRITE, True)
        glock.action_gnp_fill_specs()
        self.assertEqual(glock.gnp_magazine_capacity, 15, "overwritten with the setting on")

    def test_overwrite_never_clears(self):
        product = self.Template.create({"name": "Range bag", "gnp_brand": "Acme", "gnp_magazine_capacity": 10})
        stats = product._gnp_fill_specs(overwrite=True)
        self.assertEqual(stats, {"updated": 0, "unchanged": 0, "not_found": 1})
        self.assertEqual((product.gnp_brand, product.gnp_magazine_capacity), ("Acme", 10))

    def test_nothing_found(self):
        shirt = self.Template.create({"name": "Blue Cotton T-Shirt XL"})
        action = shirt.action_gnp_fill_specs()
        self.assertEqual(action["params"]["type"], "warning")
        self.assertFalse(shirt.gnp_product_kind)
        self.assertFalse(shirt.gnp_caliber_id)

    def test_batch_server_action(self):
        templates = self.Template.create([
            {"name": "Sig Sauer P365 XL 9mm 3.1\" 12+1 Pistol"},
            {"name": "CCI Mini-Mag 22 LR 40gr 100 Rounds", "list_price": 12.0},
            {"name": "Gift card"},
        ])
        server_action = self.env.ref("gunsnprices_product_specs.action_server_fill_specs_template")
        action = server_action.with_context(
            active_model="product.template", active_ids=templates.ids, active_id=templates[0].id).run()
        self.assertEqual(action["tag"], "display_notification")
        self.assertIn("2 updated", action["params"]["message"])
        self.assertIn("1 with no specs", action["params"]["message"])
        self.assertEqual(templates[0].gnp_model, "Sig Sauer P365 XL")
        self.assertEqual(templates[1].gnp_rounds_per_box, 100)
        self.assertAlmostEqual(templates[1].gnp_cost_per_round, 0.12, places=4)
        # second run: nothing left to change
        again = templates[:2].action_gnp_fill_specs()
        self.assertEqual(again["params"]["type"], "info")

    def test_variant_server_action(self):
        template = self.Template.create({"name": "Smith & Wesson M&P15 Sport III 5.56 NATO 16\" 30rd Rifle"})
        server_action = self.env.ref("gunsnprices_product_specs.action_server_fill_specs_variant")
        variant = template.product_variant_id
        server_action.with_context(active_model="product.product", active_ids=variant.ids, active_id=variant.id).run()
        self.assertEqual(template.gnp_model_family, "S&W M&P15")
        self.assertEqual(variant.gnp_caliber_id, self.caliber("5-56x45mmnato"))

    def test_variant_form(self):
        # the variant form is built on the template form, so it gets the Specs tab and its button
        with Form(self.env["product.product"]) as form:
            form.name = "Glock 17 Gen5 9mm 4.49in 17+1"
            form.gnp_magazine_capacity = 17
        variant = form.save()
        arch = self.env["product.product"].get_view(view_type="form")["arch"]
        self.assertIn('name="action_gnp_fill_specs"', arch)
        variant.action_gnp_fill_specs()
        self.assertEqual(variant.product_tmpl_id.gnp_model_family, "Glock 17")
        self.assertEqual(variant.gnp_magazine_capacity, 17)

    def test_glock_part_number(self):
        template = self.Template.create({"name": "Glock 19 9mm Pistol", "default_code": "PA195S203MOS"})
        template.action_gnp_fill_specs()
        self.assertEqual(template.gnp_model, "Glock 19 Gen 5 MOS", "model and generation decoded from the part number")
        self.assertEqual(template.gnp_generation, "5")

    def test_fill_on_create(self):
        before = self.Template.create({"name": "Henry Big Boy Steel .357 Mag 20\" Lever Action"})
        self.assertFalse(before.gnp_model, "setting off by default")
        set_flag(self.env, PARAM_FILL_ON_CREATE, True)
        after = self.Template.create({"name": "Henry Big Boy Steel .357 Mag 20\" Lever Action"})
        self.assertEqual(after.gnp_model, "Henry Big Boy Steel")
        self.assertEqual(after.gnp_barrel_length, 20.0)
        skipped = self.Template.with_context(gnp_no_fill=True).create({"name": "Glock 17 Gen 5 9mm"})
        self.assertFalse(skipped.gnp_model)

    def test_kind_set_by_hand_is_respected(self):
        # a name that reads like ammo ("50 Rounds of Ammo"), marked as a firearm by hand: parsed as a firearm
        name = "Glock 19 Gen 5 9mm Pistol Bundle with 50 Rounds of Ammo"
        guessed = self.Template.create({"name": name})
        guessed.action_gnp_fill_specs()
        self.assertEqual(guessed.gnp_product_kind, "ammo")
        self.assertFalse(guessed.gnp_model)
        template = self.Template.create({"name": name, "gnp_product_kind": "firearm"})
        template.action_gnp_fill_specs()
        self.assertEqual(template.gnp_product_kind, "firearm")
        self.assertEqual(template.gnp_model, "Glock 19 Gen 5")

    def test_product_form(self):
        with Form(self.Template) as form:
            form.name = "Winchester Super-X 12 Gauge 2-3/4\" 00 Buckshot 5 Rounds"
            form.list_price = 6.5
            form.gnp_rounds_per_box = 5
            form.gnp_caliber_id = self.caliber("12gauge")
        template = form.save()
        self.assertAlmostEqual(template.gnp_cost_per_round, 1.3, places=4)
        self.assertEqual(template.gnp_caliber_type, "shotgun")

    def test_settings(self):
        settings = self.env["res.config.settings"].create({"gnp_overwrite_specs": True, "gnp_fill_on_create": True})
        settings.execute()
        self.assertTrue(get_flag(self.env, PARAM_OVERWRITE))
        self.assertTrue(get_flag(self.env, PARAM_FILL_ON_CREATE))
        settings = self.env["res.config.settings"].create({"gnp_overwrite_specs": False})
        settings.execute()
        self.assertFalse(get_flag(self.env, PARAM_OVERWRITE))
        self.assertTrue(settings.gnp_parser_info.startswith("gunsnprices 0.1."))
