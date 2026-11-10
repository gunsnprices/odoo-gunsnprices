# Publishing on the Odoo Apps store (apps.odoo.com)

Researched 2026-11-10. Nothing has been published, pushed or registered yet. Quotes are from the pages linked
next to them; items marked *unconfirmed* come from forum posts or were not found on an official page.

## Which Odoo versions

Odoo's support table (https://www.odoo.com/documentation/19.0/administration/standard_extended_support.html):

| Version | Released | Standard support until |
|---------|----------|------------------------|
| 20.0 | September 2026 | September 2029 (planned) |
| 19.0 | September 2025 | September 2028 (planned) |
| 18.0 | October 2024 | September 2027 (planned) |
| 17.0 | November 2023 | September 2026 (ended; extended support only) |

The store lists apps for 20.0 already (browse filter "series=20.0":
https://apps.odoo.com/apps/modules/browse?series=20.0). Python: 18.0 and 19.0 need 3.10 or later, 20.0 needs 3.12
or later (https://www.odoo.com/documentation/20.0/administration/on_premise/source.html).

Plan: publish the three supported series, 18.0, 19.0 and 20.0, one branch each. This repository has the 18.0
branch. 19.0 and 20.0 are the same code after `tools/port_to.py`, which changes the manifest version and, for 20.0,
turns `security/ir.model.access.csv` into `security/ir.access.csv`. Odoo 20 replaced `ir.model.access` with
`ir.access`.

## Repository layout the store expects

- One folder per module at the repository root, each with its `__manifest__.py`. The scanner's error message says:
  "Each module needs to be in a separate folder at the root of the repository, even if there is only one module"
  (https://www.odoo.com/forum/help-1/repository-module-odoo-apps-260555). Here that folder is
  `gunsnprices_product_specs/`. `tools/`, `tests/` and `.github/` have no manifest and are not modules.
- One branch per Odoo series, named after the series (`18.0`, `19.0`, `20.0`). Each branch is registered separately
  with `#<branch>` at the end of the URL. The FAQ example is `ssh://git@github.com/odoo/odoo#9.0`; the
  one-branch-per-version advice comes from a forum answer
  (https://www.odoo.com/de_DE/forum/hilfe-1/update-apps-to-v18-267281). *Unconfirmed: whether a branch with
  another name is refused.*
- Keep the same technical name (`gunsnprices_product_specs`) on every branch. The guidelines say to use the same
  module name for each Odoo version (https://apps.odoo.com/apps/vendor-guidelines).

## Steps

1. **Create the GitHub repository**, public, for example `github.com/gunsnprices/odoo-gunsnprices`, and push:

   ```sh
   git remote add origin git@github.com:gunsnprices/odoo-gunsnprices.git
   git push -u origin 18.0
   ```

2. **Make the 19.0 and 20.0 branches** (CI runs the Odoo tests for the series named by the branch):

   ```sh
   git switch -c 19.0 18.0 && python tools/port_to.py 19.0 && git commit -am "Port to Odoo 19.0" && git push -u origin 19.0
   git switch -c 20.0 18.0 && python tools/port_to.py 20.0 && git add -A && git commit -m "Port to Odoo 20.0" && git push -u origin 20.0
   ```

   Later fixes go on 18.0 first and are merged or cherry-picked forward.

3. **Sign in** at odoo.com with the account that will own the listing (the vendor account), then open
   https://apps.odoo.com/apps/upload. Registering a repository requires being logged in.

4. **Register each branch** with its SSH URL (format from the FAQ, https://apps.odoo.com/apps/faq):

   ```
   ssh://git@github.com/gunsnprices/odoo-gunsnprices#18.0
   ssh://git@github.com/gunsnprices/odoo-gunsnprices#19.0
   ssh://git@github.com/gunsnprices/odoo-gunsnprices#20.0
   ```

   The FAQ gives the general form `ssh://git@gitServer(:port)/mypath#version`: "only use the colon to define the
   port … if no port is to be defined, use slash to separate gitServer from mypath". Its GitHub example has no
   `.git` suffix. *Unconfirmed: whether `.git` is accepted; leave it out.*

5. **Access.** For a private repository, Odoo must be allowed to read it: "If you are on Github, you can simply
   authorize our online-odoo user (NOT odoo-online) on your repository (the authorization must be done on the
   repository specifically, not the entire company)" (https://apps.odoo.com/apps/faq). For GitLab, add
   `OdooApps (apps@odoo.com)`. For Bitbucket and other hosts, use the SSH key from
   https://apps.odoo.com/apps/repository-keys. *Unconfirmed: whether a public repository needs anything. Adding
   `online-odoo` as a read-only collaborator does no harm.*

6. **Scan.** The store scans the registered branches. The vendor dashboard (https://apps.odoo.com/apps/dashboard/repos)
   has a manual scan button (forum: https://www.odoo.com/forum/help-1/manual-repo-scan-is-not-working-in-appsodoocom-290855).
   *Unconfirmed: the automatic rescan schedule. A forum post suggests daily.* "A good manifest is essential as any
   error will unpublish all the modules from your repository" (https://apps.odoo.com/apps/vendor-guidelines).

7. **Check the listing**, expected at https://apps.odoo.com/apps/modules/18.0/gunsnprices_product_specs (and
   `/19.0/`, `/20.0/`):
   - icon `static/description/icon.png`;
   - cover from the manifest `images` key (`static/description/banner.png`, 560×280);
   - description from `static/description/index.html`;
   - "Website" showing https://gunsnprices.com. The store shows the manifest `website` as "Website" on module
     pages; seen on https://apps.odoo.com/apps/modules/18.0/web_responsive;
   - license LGPL-3, price Free.

8. **Updates:** bump `version` in the manifest (for example `18.0.1.0.1`), update CHANGELOG.md, push. The store picks
   it up at the next scan, or use the manual scan.

## Rules that apply to this module

From the vendor guidelines (https://apps.odoo.com/apps/vendor-guidelines) unless noted.

**Manifest**

- The name "must be explicit and should contain no more than 25 characters. Avoid adjectives, or including the name
  of your company." That is why the name is "Firearm & Ammo Specs" (20 characters) and not "GunsNPrices …". The
  author is still "GunsNPrices".
- The version must include the Odoo series (`18.0.1.0.0`).
- `license`, `depends` and the other manifest keys are documented at
  https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html.
- "the list must contains all the dependencies needed to run the module." The module depends only on `product`.

**Price**

- "If the price is not set, the application is free (same case if the price is negative)." The manifest has no
  `price` key, so the app is free. A `price` of 0 is not documented, and the minimum price for a paid app is 9 EUR.
- "Support services are not required for free apps."
- Paid apps only: "Odoo S.A. takes a 30% commission on all sales on Odoo Apps and a 25% commission on each In-App
  Purchase (IAP) transactions." Payouts happen monthly once unredeemed sales reach 400 EUR
  (https://apps.odoo.com/apps/faq).

**License**

- "any license can be applie[d] to your app, as long as it respects the licenses of its dependencies", with LGPL-3
  recommended for open source and OPL-1 for proprietary apps. A missing license lowers the ranking.
- Here: module LGPL-3, bundled parser MIT, data CC BY 4.0. MIT and CC BY 4.0 allow redistribution inside an
  LGPL-3 module as long as their notices are kept (`lib/gunsnprices/LICENSE`, `LICENSE-DATA`) and the data source
  is credited. The store page credits it in plain text.

**Description page (`static/description/index.html`)**

- In English.
- "Neither the description nor the manifest of a module shall mention promotions, advertisements or links to
  another app store or external platform."
- Links: "You can link against resources provided in your static/description folder", "You can use youtube links
  (please use canonical links) and microsoft teams links, any other external link will be invalidated", "You can
  use mailto: and skype: prefixes".
- "You cannot insert static tags, static widgets or modals in your description", "You cannot inject JavaScript",
  "use bootstrap 4 classes and color, font-\*, margin-\*, padding-\*, border-\* attributes".
- Images: png, gif or jpeg only (https://apps.odoo.com/apps/faq). Icon at `static/description/icon.png`, and it
  must really be a PNG.
- The app "cannot serve as a simple advertisement".
- `tests/test_package.py` checks the page against these rules: no script/iframe/style/form tags, no `on*`
  attributes, only allowed link targets, local png/gif/jpeg images only, inline styles limited to
  color/font/margin/padding/border.

**Ranking.** A listing ranks lower when "The module has no icon", "no cover image (thumbnail)", "License is not set",
"a rating that is quite poor (lower than 3)", or "a non-html description".

**Behaviour**

- "The module should be installable by copying it in the addons folder, and satisfying dependencies. Avoid other
  installation procedures." That is one reason the parser is bundled instead of declared in
  `external_dependencies`: Odoo refuses to install a module whose external Python dependency is missing ("Unable to
  install module … because an external dependency is not met").
- No downloading or running other code and no obfuscated code. External services must be "clearly advertised";
  data sent elsewhere needs an explanation and user opt-in. This module calls no external service.
- "Odoo reserves the right to unpublish any App at any point without prior notice." Not every module is reviewed;
  Odoo acts on reports.

**Where it can run**

- Odoo Online (SaaS): "Third-party apps sold on Odoo Apps cannot be used on Odoo Online, unless they are
  data-modules (that do not include any python files)" (https://apps.odoo.com/apps/faq). This module has Python
  code, so it is for Odoo.sh and on-premise only.
- Odoo.sh: third-party apps are fine in private Odoo.sh repositories, and "Public repositories should only host
  free modules" (FAQ). Odoo.sh installs a `requirements.txt` at the root of the branch: "The platform will ensure
  these dependencies are installed in your containers"
  (https://www.odoo.com/documentation/18.0/administration/odoo_sh/advanced.html). Not needed for this module.
  Anyone who wants a newer parser can add `gunsnprices>=0.1,<0.2` there.

## Decisions for the owner

- **GitHub repository name and visibility.** Proposed: public `gunsnprices/odoo-gunsnprices`, which suits a free
  module.
- **Which odoo.com account owns the listing.** Vendor and support contact: app@gunsnprices.com is used on the
  store page.
- **The manifest `website`** is https://gunsnprices.com, as requested. It is the standard author-website key, and
  other vendors set theirs. The description page itself has no external links, only a plain-text credit
  "GunsNPrices (gunsnprices.com)", as the CC BY 4.0 data license asks. The caliber records carry their
  gunsnprices.com reference page as a field inside the app. If a reviewer objects, that field and the credit can
  be reduced without functional loss.
- **Whether to publish 18.0 only, or 18.0 + 19.0 + 20.0.** All three pass the module tests locally.

## Sources

- Upload / register page and FAQ: https://apps.odoo.com/apps/upload, https://apps.odoo.com/apps/faq
- Vendor guidelines: https://apps.odoo.com/apps/vendor-guidelines
- Repository SSH keys: https://apps.odoo.com/apps/repository-keys
- Vendor dashboard (repositories): https://apps.odoo.com/apps/dashboard/repos
- Sales conditions: https://apps.odoo.com/apps/sales-conditions
- Supported versions: https://www.odoo.com/documentation/19.0/administration/standard_extended_support.html
- Module manifest reference: https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html
- Odoo.sh requirements.txt: https://www.odoo.com/documentation/18.0/administration/odoo_sh/advanced.html
- Install from source / Python versions: https://www.odoo.com/documentation/20.0/administration/on_premise/source.html
- Official description template (linked from the upload page):
  https://github.com/odoo/odoo/blob/11.0/addons/crm/static/description/index.html
